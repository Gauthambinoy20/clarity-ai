"""
Adversarial humanization pipeline -- iteratively rewrites text through
lexical, structural, and LLM layers until the AI detection score drops
below a target threshold, while preserving meaning and originality.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class HumanizationResult:
    original_text: str
    humanized_text: str
    original_score: float
    final_score: float
    score_timeline: List[Dict[str, Any]]
    iterations: int
    quality_metrics: Dict[str, float]
    targets_met: bool


class AdversarialHumanizationPipeline:
    """
    Multi-layer adversarial humanization with detection-in-the-loop.

    Flow
    ----
    1. Score baseline text with the detection ensemble.
    2. Layer 1 -- lexical replacements (buzzwords, contractions, AI phrases).
    3. Layer 2 -- structural changes (sentence variation, fragments, hedging).
    4. Layer 3 -- Ollama LLM rewrite.
    5. Adversarial loop -- if score still above target, re-apply layers 2-3
       with increasing temperature (max 5 iterations).
    6. Post-humanization plagiarism check + meaning preservation check.
    """

    def __init__(
        self,
        target_ai_score: float = 0.10,
        target_plag_score: float = 0.10,
        max_iterations: int = 5,
        base_temperature: float = 0.85,
        similarity_threshold: float = 0.80,
    ) -> None:
        self.target_ai_score = target_ai_score
        self.target_plag_score = target_plag_score
        self.max_iterations = max_iterations
        self.base_temperature = base_temperature
        self.similarity_threshold = similarity_threshold

        # Lazy-loaded components
        self._lexical = None
        self._structural = None
        self._ollama = None
        self._similarity_model = None

    # ------------------------------------------------------------------
    # Lazy loaders
    # ------------------------------------------------------------------
    def _get_lexical(self):
        if self._lexical is None:
            from app.ml.humanizer.lexical_humanizer import LexicalHumanizer

            self._lexical = LexicalHumanizer()
        return self._lexical

    def _get_structural(self):
        if self._structural is None:
            from app.ml.humanizer.structural_humanizer import StructuralHumanizer

            self._structural = StructuralHumanizer()
        return self._structural

    def _get_ollama(self):
        if self._ollama is None:
            from app.ml.humanizer.ollama_humanizer import OllamaHumanizer

            self._ollama = OllamaHumanizer()
        return self._ollama

    def _get_similarity_model(self):
        if self._similarity_model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._similarity_model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("Sentence similarity model loaded.")
            except Exception as exc:
                logger.warning("Could not load sentence-transformers: %s", exc)
        return self._similarity_model

    # ------------------------------------------------------------------
    # Detection scoring helper
    # ------------------------------------------------------------------
    async def _score_text(self, text: str) -> float:
        """
        Run the detection ensemble on text and return the overall AI score.
        Falls back to 0.5 if detection pipeline is unavailable.
        """
        try:
            from app.ml.ensemble.meta_learner import EnsembleMetaLearner

            # We need to get signal results; import detector infrastructure
            # if a full pipeline exists; otherwise use the meta-learner with
            # whatever signals we can gather.
            try:
                # Try importing a detection pipeline if one exists
                from app.ml.ensemble import detection_pipeline  # type: ignore

                results = detection_pipeline.analyze(text)
                if isinstance(results, dict) and "overall_score" in results:
                    return float(results["overall_score"])
                # If results is a dict of signal results, use meta learner
                learner = EnsembleMetaLearner()
                prediction = learner.predict(results)
                return float(prediction["overall_score"])
            except (ImportError, AttributeError):
                # No full pipeline yet; do a lightweight heuristic score
                return self._heuristic_ai_score(text)
        except Exception as exc:
            logger.warning("Detection scoring failed: %s", exc)
            return 0.5

    @staticmethod
    def _heuristic_ai_score(text: str) -> float:
        """
        Quick heuristic AI score when full detection pipeline is unavailable.
        Uses simple statistical proxies.
        """
        words = text.split()
        if not words:
            return 0.5

        # Average word length (AI text tends to use longer words)
        avg_word_len = sum(len(w) for w in words) / len(words)

        # Sentence length variance (low variance = more AI-like)
        import re

        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) > 1:
            lens = [len(s.split()) for s in sentences]
            mean_len = sum(lens) / len(lens)
            variance = sum((length - mean_len) ** 2 for length in lens) / len(lens)
        else:
            variance = 0.0

        # Simple scoring
        score = 0.5
        if avg_word_len > 5.5:
            score += 0.1
        if variance < 15.0:
            score += 0.1
        if avg_word_len < 4.5 and variance > 30.0:
            score -= 0.15

        return max(0.0, min(1.0, score))

    # ------------------------------------------------------------------
    # Meaning preservation
    # ------------------------------------------------------------------
    def _compute_similarity(self, text_a: str, text_b: str) -> float:
        """Cosine similarity between sentence embeddings."""
        model = self._get_similarity_model()
        if model is None:
            # Fallback: crude word-overlap Jaccard
            return self._word_overlap_similarity(text_a, text_b)

        try:
            embeddings = model.encode([text_a, text_b], convert_to_numpy=True)
            import numpy as np

            cos_sim = float(
                np.dot(embeddings[0], embeddings[1])
                / (np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1]) + 1e-10)
            )
            return cos_sim
        except Exception as exc:
            logger.warning("Similarity computation failed: %s", exc)
            return self._word_overlap_similarity(text_a, text_b)

    @staticmethod
    def _word_overlap_similarity(a: str, b: str) -> float:
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union) if union else 0.0

    # ------------------------------------------------------------------
    # Plagiarism check helper
    # ------------------------------------------------------------------
    async def _check_plagiarism(self, original: str, humanized: str) -> float:
        """
        Quick plagiarism check between original and humanized text.
        Returns a plagiarism score 0-1.
        """
        try:
            from app.ml.plagiarism.exact_match import ExactMatcher

            matcher = ExactMatcher()
            result = matcher.compare(original, humanized)
            return result.get("jaccard_similarity", 0.0)
        except (ImportError, Exception) as exc:
            logger.debug("Plagiarism check skipped: %s", exc)
            # Fallback: simple word overlap as proxy
            return self._word_overlap_similarity(original, humanized)

    # ------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------
    async def humanize(
        self,
        text: str,
        style: str = "academic",
        model: str = "mistral:7b-instruct",
    ) -> HumanizationResult:
        """
        Run the full adversarial humanization pipeline.

        Returns a HumanizationResult with all metrics.
        """
        start_time = time.time()
        score_timeline: List[Dict[str, Any]] = []

        # ---- Baseline score ----
        original_score = await self._score_text(text)
        score_timeline.append(
            {
                "stage": "baseline",
                "score": round(original_score, 4),
                "elapsed_s": 0.0,
            }
        )

        current_text = text

        # If already below target, skip processing
        if original_score <= self.target_ai_score:
            return HumanizationResult(
                original_text=text,
                humanized_text=text,
                original_score=round(original_score, 4),
                final_score=round(original_score, 4),
                score_timeline=score_timeline,
                iterations=0,
                quality_metrics={
                    "meaning_similarity": 1.0,
                    "plagiarism_score": 0.0,
                },
                targets_met=True,
            )

        # ---- Layer 1: Lexical ----
        lexical = self._get_lexical()
        current_text = lexical.humanize(current_text)
        layer1_score = await self._score_text(current_text)
        score_timeline.append(
            {
                "stage": "lexical",
                "score": round(layer1_score, 4),
                "elapsed_s": round(time.time() - start_time, 2),
            }
        )

        # ---- Layer 2: Structural ----
        structural = self._get_structural()
        current_text = structural.humanize(current_text, style=style)
        layer2_score = await self._score_text(current_text)
        score_timeline.append(
            {
                "stage": "structural",
                "score": round(layer2_score, 4),
                "elapsed_s": round(time.time() - start_time, 2),
            }
        )

        # ---- Layer 3: Ollama LLM rewrite ----
        ollama = self._get_ollama()
        current_text = await ollama.humanize(
            current_text,
            style=style,
            model=model,
            temperature=self.base_temperature,
        )
        layer3_score = await self._score_text(current_text)
        score_timeline.append(
            {
                "stage": "ollama",
                "score": round(layer3_score, 4),
                "elapsed_s": round(time.time() - start_time, 2),
            }
        )

        # ---- Adversarial loop ----
        iteration = 0
        current_score = layer3_score
        while current_score > self.target_ai_score and iteration < self.max_iterations:
            iteration += 1
            temp = min(self.base_temperature + (iteration * 0.05), 1.2)

            # Re-apply structural variation
            current_text = structural.humanize(current_text, style=style)

            # Re-apply Ollama with increased temperature
            current_text = await ollama.humanize(
                current_text,
                style=style,
                model=model,
                temperature=temp,
            )

            # Check meaning preservation
            similarity = self._compute_similarity(text, current_text)
            if similarity < self.similarity_threshold:
                logger.warning(
                    "Iteration %d: meaning similarity dropped to %.3f (below %.3f). "
                    "Stopping to preserve meaning.",
                    iteration,
                    similarity,
                    self.similarity_threshold,
                )
                break

            current_score = await self._score_text(current_text)
            score_timeline.append(
                {
                    "stage": f"adversarial_iter_{iteration}",
                    "score": round(current_score, 4),
                    "temperature": round(temp, 3),
                    "similarity": round(similarity, 4),
                    "elapsed_s": round(time.time() - start_time, 2),
                }
            )

        # ---- Post-humanization quality checks ----
        final_similarity = self._compute_similarity(text, current_text)
        plag_score = await self._check_plagiarism(text, current_text)
        final_score = current_score

        targets_met = final_score <= self.target_ai_score and plag_score <= self.target_plag_score

        quality_metrics = {
            "meaning_similarity": round(final_similarity, 4),
            "plagiarism_score": round(plag_score, 4),
            "word_count_original": len(text.split()),
            "word_count_humanized": len(current_text.split()),
            "processing_time_s": round(time.time() - start_time, 2),
        }

        return HumanizationResult(
            original_text=text,
            humanized_text=current_text,
            original_score=round(original_score, 4),
            final_score=round(final_score, 4),
            score_timeline=score_timeline,
            iterations=iteration,
            quality_metrics=quality_metrics,
            targets_met=targets_met,
        )
