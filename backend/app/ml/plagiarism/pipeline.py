"""
Full plagiarism detection pipeline -- orchestrates key-phrase extraction,
source discovery, content fetching, exact matching, semantic matching,
and per-paragraph scoring into a single cohesive result.
"""

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _split_paragraphs(text: str) -> List[str]:
    """Split text into paragraphs on double-newlines or single newlines
    followed by a blank line, stripping empties."""
    paras = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paras if p.strip() and len(p.split()) >= 5]


def _split_sentences(text: str) -> List[str]:
    sents = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sents if s.strip() and len(s.split()) >= 3]


class PlagiarismPipeline:
    """
    End-to-end plagiarism analysis.

    Steps
    -----
    1. Extract key phrases from the input text.
    2. Search multiple sources in parallel.
    3. Fetch content from discovered URLs.
    4. Run exact-match (Winnowing + Jaccard + LCS) against each source.
    5. Run semantic-match (sentence embeddings) against each source.
    6. Compile per-paragraph plagiarism scores.
    7. Produce source attribution and overall originality score.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.80,
        max_sources_to_compare: int = 10,
    ) -> None:
        self.similarity_threshold = similarity_threshold
        self.max_sources_to_compare = max_sources_to_compare

        # Lazy-loaded components
        self._source_discovery = None
        self._exact_matcher = None
        self._semantic_matcher = None

    # ------------------------------------------------------------------
    # Lazy loaders
    # ------------------------------------------------------------------
    def _get_source_discovery(self):
        if self._source_discovery is None:
            from app.ml.plagiarism.source_discovery import SourceDiscovery

            self._source_discovery = SourceDiscovery()
        return self._source_discovery

    def _get_exact_matcher(self):
        if self._exact_matcher is None:
            from app.ml.plagiarism.exact_match import ExactMatcher

            self._exact_matcher = ExactMatcher()
        return self._exact_matcher

    def _get_semantic_matcher(self):
        if self._semantic_matcher is None:
            from app.ml.plagiarism.semantic_match import SemanticMatcher

            self._semantic_matcher = SemanticMatcher()
        return self._semantic_matcher

    # ------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------
    async def analyze(self, text: str) -> Dict[str, Any]:
        """
        Run the full plagiarism pipeline on *text*.

        Returns
        -------
        dict with keys:
            overall_plagiarism_score  : float 0-1
            originality_percentage    : float 0-100
            paragraph_analysis        : list of per-paragraph results
            sources_found             : list of matched source dicts
            key_phrases               : list of extracted query phrases
            summary                   : human-readable summary string
        """
        if not text or not text.strip():
            return self._empty_result()

        paragraphs = _split_paragraphs(text)
        if not paragraphs:
            paragraphs = [text]

        # ---- Step 1-3: Discover and fetch sources ----
        discovery = self._get_source_discovery()
        search_result = await discovery.search_and_fetch(text)

        key_phrases = search_result.get("key_phrases", [])
        sources = search_result.get("sources", [])
        fetched_content = search_result.get("fetched_content", {})

        # Build a list of (source_meta, source_text) for comparison
        source_texts: List[Dict[str, Any]] = []
        for src in sources[: self.max_sources_to_compare]:
            url = src.get("url", "")
            content = fetched_content.get(url, "")
            # Use snippet if no fetched content
            if not content:
                content = src.get("snippet", "")
            if content and len(content.split()) >= 10:
                source_texts.append(
                    {
                        "meta": src,
                        "content": content,
                    }
                )

        # ---- Step 4-5: Compare each paragraph against each source ----
        exact_matcher = self._get_exact_matcher()
        semantic_matcher = self._get_semantic_matcher()

        paragraph_analysis: List[Dict[str, Any]] = []
        all_matched_sources: List[Dict[str, Any]] = []

        for para_idx, paragraph in enumerate(paragraphs):
            para_result = {
                "paragraph_index": para_idx,
                "text": paragraph[:200] + ("..." if len(paragraph) > 200 else ""),
                "word_count": len(paragraph.split()),
                "max_exact_overlap": 0.0,
                "max_semantic_similarity": 0.0,
                "plagiarism_score": 0.0,
                "matched_source": None,
                "match_details": [],
            }

            best_score = 0.0
            best_source = None

            for st in source_texts:
                source_content = st["content"]
                source_meta = st["meta"]

                # Exact match
                exact_result = exact_matcher.compare(paragraph, source_content)
                exact_overlap = exact_result.get("overlap_score", 0.0)

                # Semantic match
                semantic_result = semantic_matcher.compare(paragraph, source_content)
                semantic_sim = semantic_result.get("overall_semantic_similarity", 0.0)
                flagged_ratio = semantic_result.get("flagged_sentence_ratio", 0.0)

                # Combined paragraph-source score
                combined = max(
                    exact_overlap,
                    0.7 * semantic_sim + 0.3 * flagged_ratio,
                )

                match_detail = {
                    "source_title": source_meta.get("title", "Unknown"),
                    "source_url": source_meta.get("url", ""),
                    "source_engine": source_meta.get("source_engine", ""),
                    "exact_overlap": round(exact_overlap, 4),
                    "semantic_similarity": round(semantic_sim, 4),
                    "combined_score": round(combined, 4),
                    "exact_copies": semantic_result.get("exact_copies", 0),
                    "paraphrases": semantic_result.get("close_paraphrases", 0),
                    "lcs": exact_result.get("longest_common_substring", {}),
                }

                para_result["match_details"].append(match_detail)

                if combined > best_score:
                    best_score = combined
                    best_source = match_detail

                if exact_overlap > para_result["max_exact_overlap"]:
                    para_result["max_exact_overlap"] = round(exact_overlap, 4)
                if semantic_sim > para_result["max_semantic_similarity"]:
                    para_result["max_semantic_similarity"] = round(semantic_sim, 4)

            para_result["plagiarism_score"] = round(best_score, 4)
            para_result["matched_source"] = best_source

            # Only keep top matches in detail to reduce payload
            para_result["match_details"] = sorted(
                para_result["match_details"],
                key=lambda d: d["combined_score"],
                reverse=True,
            )[:3]

            paragraph_analysis.append(para_result)

            # Collect significantly matching sources
            if best_source and best_score >= self.similarity_threshold:
                if best_source not in all_matched_sources:
                    all_matched_sources.append(best_source)

        # ---- Step 6: Aggregate overall score ----
        if paragraph_analysis:
            para_scores = [p["plagiarism_score"] for p in paragraph_analysis]
            # Overall score: weighted by paragraph length
            total_words = sum(p["word_count"] for p in paragraph_analysis)
            if total_words > 0:
                overall_score = (
                    sum(p["plagiarism_score"] * p["word_count"] for p in paragraph_analysis)
                    / total_words
                )
            else:
                overall_score = sum(para_scores) / len(para_scores)
        else:
            overall_score = 0.0

        overall_score = round(min(overall_score, 1.0), 4)
        originality = round((1.0 - overall_score) * 100, 2)

        # ---- Step 7: Source attribution summary ----
        sources_found = []
        seen_urls = set()
        for ms in all_matched_sources:
            url = ms.get("source_url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                sources_found.append(
                    {
                        "title": ms.get("source_title", ""),
                        "url": url,
                        "engine": ms.get("source_engine", ""),
                        "max_similarity": ms.get("combined_score", 0.0),
                    }
                )

        summary = self._build_summary(overall_score, originality, paragraph_analysis, sources_found)

        return {
            "overall_plagiarism_score": overall_score,
            "originality_percentage": originality,
            "paragraph_analysis": paragraph_analysis,
            "sources_found": sources_found,
            "key_phrases": key_phrases,
            "summary": summary,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _empty_result() -> Dict[str, Any]:
        return {
            "overall_plagiarism_score": 0.0,
            "originality_percentage": 100.0,
            "paragraph_analysis": [],
            "sources_found": [],
            "key_phrases": [],
            "summary": "No text provided for plagiarism analysis.",
        }

    @staticmethod
    def _build_summary(
        score: float,
        originality: float,
        paragraphs: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
    ) -> str:
        parts: List[str] = []

        pct = int(round(score * 100))
        if score < 0.10:
            parts.append(f"This text appears highly original ({originality}% originality).")
        elif score < 0.30:
            parts.append(
                f"Minor similarities detected ({pct}% potential overlap). "
                f"The text is {originality}% original."
            )
        elif score < 0.60:
            parts.append(
                f"Moderate similarities found ({pct}% potential overlap). "
                "Some passages may need review."
            )
        else:
            parts.append(
                f"Significant similarities detected ({pct}% potential overlap). "
                "Multiple passages closely match existing sources."
            )

        flagged = [p for p in paragraphs if p["plagiarism_score"] >= 0.50]
        if flagged:
            parts.append(f"{len(flagged)} of {len(paragraphs)} paragraphs flagged for review.")

        if sources:
            parts.append(f"{len(sources)} potential source(s) identified.")

        return " ".join(parts)
