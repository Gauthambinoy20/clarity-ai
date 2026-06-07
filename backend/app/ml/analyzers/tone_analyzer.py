"""
Tone and sentiment analysis engine for ClarityAI.

Uses spaCy and keyword dictionaries (no external API calls).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keyword dictionaries
# ---------------------------------------------------------------------------

_POSITIVE_WORDS: set[str] = {
    "good",
    "great",
    "excellent",
    "amazing",
    "wonderful",
    "fantastic",
    "superb",
    "outstanding",
    "brilliant",
    "beautiful",
    "love",
    "happy",
    "joy",
    "delight",
    "pleased",
    "thrilled",
    "grateful",
    "thankful",
    "impressed",
    "inspire",
    "inspiring",
    "success",
    "successful",
    "win",
    "winning",
    "achieve",
    "achievement",
    "benefit",
    "beneficial",
    "perfect",
    "ideal",
    "exceptional",
    "remarkable",
    "terrific",
    "positive",
    "advantage",
    "admire",
    "appreciate",
    "cheerful",
    "confident",
    "creative",
    "eager",
    "elegant",
    "enjoy",
    "enthusiastic",
    "exciting",
    "fabulous",
    "fortunate",
    "generous",
    "genuine",
    "glad",
    "graceful",
    "harmonious",
    "helpful",
    "honest",
    "incredible",
    "innovative",
    "joyful",
    "kind",
    "magnificent",
    "marvelous",
    "optimistic",
    "passionate",
    "peaceful",
    "pleasant",
    "proud",
    "refreshing",
    "reliable",
    "satisfying",
    "splendid",
    "stunning",
    "supportive",
    "triumphant",
    "valuable",
    "vibrant",
    "warm",
    "worthy",
}

_NEGATIVE_WORDS: set[str] = {
    "bad",
    "terrible",
    "awful",
    "horrible",
    "poor",
    "worst",
    "ugly",
    "hate",
    "sad",
    "angry",
    "disappointed",
    "frustrating",
    "annoying",
    "failure",
    "fail",
    "failed",
    "problem",
    "issue",
    "difficult",
    "impossible",
    "wrong",
    "mistake",
    "error",
    "weakness",
    "weak",
    "danger",
    "dangerous",
    "fear",
    "fearful",
    "worried",
    "worry",
    "threat",
    "threatening",
    "damage",
    "destroy",
    "destruction",
    "harmful",
    "negative",
    "pain",
    "painful",
    "suffer",
    "suffering",
    "tragic",
    "unfortunately",
    "unpleasant",
    "useless",
    "worthless",
    "dreadful",
    "miserable",
    "pathetic",
    "inferior",
    "lousy",
    "abysmal",
    "appalling",
    "atrocious",
    "catastrophic",
    "deplorable",
    "detrimental",
    "disastrous",
    "disgraceful",
    "dreadful",
    "grim",
    "hopeless",
    "inadequate",
    "inferior",
    "mediocre",
    "negligent",
    "offensive",
    "regrettable",
    "shameful",
    "shocking",
    "toxic",
    "troublesome",
    "unacceptable",
    "vile",
    "wretched",
}

_CONFIDENT_WORDS: set[str] = {
    "certainly",
    "definitely",
    "undoubtedly",
    "clearly",
    "obviously",
    "surely",
    "absolutely",
    "indeed",
    "without doubt",
    "unquestionably",
    "proven",
    "guarantee",
    "confident",
    "assert",
    "affirm",
    "establish",
    "demonstrate",
    "evident",
    "decisive",
    "conclusive",
    "certain",
    "convinced",
    "know",
    "always",
    "never",
    "must",
    "will",
}

_TENTATIVE_WORDS: set[str] = {
    "maybe",
    "perhaps",
    "possibly",
    "might",
    "could",
    "seem",
    "seems",
    "appear",
    "appears",
    "suggest",
    "suggests",
    "likely",
    "unlikely",
    "probably",
    "approximately",
    "somewhat",
    "rather",
    "fairly",
    "quite",
    "tend",
    "tends",
    "apparently",
    "allegedly",
    "conceivably",
    "presumably",
    "supposedly",
    "generally",
    "typically",
    "usually",
    "sometimes",
    "often",
}

_ANALYTICAL_WORDS: set[str] = {
    "analyze",
    "analysis",
    "therefore",
    "consequently",
    "furthermore",
    "moreover",
    "however",
    "nevertheless",
    "whereas",
    "compare",
    "contrast",
    "evaluate",
    "examine",
    "investigate",
    "hypothesis",
    "evidence",
    "data",
    "significant",
    "correlation",
    "conclude",
    "conclusion",
    "finding",
    "result",
    "indicate",
    "suggests",
    "framework",
    "methodology",
    "systematic",
    "empirical",
    "theoretical",
    "quantitative",
    "qualitative",
    "objective",
    "criterion",
    "variable",
    "factor",
    "component",
    "mechanism",
    "principle",
}

_JOYFUL_WORDS: set[str] = {
    "happy",
    "joy",
    "joyful",
    "delighted",
    "thrilled",
    "excited",
    "ecstatic",
    "elated",
    "overjoyed",
    "cheerful",
    "blissful",
    "celebrate",
    "celebration",
    "laugh",
    "laughter",
    "smile",
    "fun",
    "wonderful",
    "fantastic",
    "amazing",
    "love",
    "loving",
    "adore",
    "pleasure",
    "paradise",
    "dream",
    "magical",
    "glorious",
    "euphoria",
    "jubilant",
    "merry",
    "playful",
    "radiant",
}

_ANGRY_WORDS: set[str] = {
    "angry",
    "furious",
    "rage",
    "outrage",
    "outraged",
    "infuriate",
    "infuriated",
    "livid",
    "enraged",
    "hostile",
    "aggressive",
    "violent",
    "attack",
    "condemn",
    "denounce",
    "despise",
    "resent",
    "resentment",
    "bitter",
    "bitterness",
    "hate",
    "hatred",
    "revenge",
    "retaliate",
    "demand",
    "unacceptable",
    "intolerable",
    "appalling",
    "disgraceful",
    "inexcusable",
    "absurd",
    "ridiculous",
    "outrageous",
}

_SAD_WORDS: set[str] = {
    "sad",
    "sorrow",
    "sorrowful",
    "grief",
    "grieving",
    "mourn",
    "mourning",
    "depressed",
    "depression",
    "melancholy",
    "gloomy",
    "gloom",
    "despair",
    "hopeless",
    "heartbroken",
    "lonely",
    "loneliness",
    "regret",
    "regretful",
    "miserable",
    "tragic",
    "tragedy",
    "loss",
    "lost",
    "suffer",
    "suffering",
    "weep",
    "tears",
    "cry",
    "crying",
    "anguish",
    "desolate",
    "forlorn",
}

_URGENT_WORDS: set[str] = {
    "immediately",
    "urgent",
    "urgently",
    "asap",
    "now",
    "critical",
    "emergency",
    "deadline",
    "hurry",
    "quickly",
    "fast",
    "rapid",
    "swift",
    "instant",
    "crucial",
    "vital",
    "imperative",
    "essential",
    "pressing",
    "time-sensitive",
    "overdue",
    "expedite",
    "priority",
    "alert",
    "warning",
    "act now",
    "don't wait",
    "limited time",
    "before it's too late",
}

_FORMAL_MARKERS: set[str] = {
    "furthermore",
    "moreover",
    "consequently",
    "nevertheless",
    "henceforth",
    "wherein",
    "whereby",
    "thereof",
    "herein",
    "notwithstanding",
    "aforementioned",
    "subsequently",
    "accordingly",
    "thus",
    "hence",
    "therefore",
    "regarding",
    "pertaining",
    "pursuant",
    "shall",
}

_CONTRACTIONS: set[str] = {
    "don't",
    "doesn't",
    "didn't",
    "can't",
    "couldn't",
    "wouldn't",
    "shouldn't",
    "won't",
    "isn't",
    "aren't",
    "wasn't",
    "weren't",
    "haven't",
    "hasn't",
    "hadn't",
    "they're",
    "we're",
    "you're",
    "i'm",
    "he's",
    "she's",
    "it's",
    "that's",
    "there's",
    "here's",
    "what's",
    "who's",
    "let's",
    "i've",
    "you've",
    "we've",
    "they've",
    "i'll",
    "you'll",
    "he'll",
    "she'll",
    "we'll",
    "they'll",
    "i'd",
    "you'd",
    "he'd",
    "she'd",
    "we'd",
    "they'd",
    "gonna",
    "wanna",
    "gotta",
    "kinda",
    "sorta",
    "y'all",
    "ain't",
}


def _load_spacy():
    """Lazy-load spaCy model."""
    try:
        import spacy

        try:
            return spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model en_core_web_sm not found; downloading...")
            from spacy.cli import download

            download("en_core_web_sm")
            return spacy.load("en_core_web_sm")
    except ImportError:
        logger.warning("spaCy not installed — tone analysis will use fallback")
        return None


class ToneAnalyzer:
    """Analyzes tone, sentiment, and emotional characteristics of text."""

    def __init__(self) -> None:
        self._nlp = None

    @property
    def nlp(self):
        if self._nlp is None:
            self._nlp = _load_spacy()
        return self._nlp

    def analyze(self, text: str) -> Dict[str, Any]:
        """Run full tone analysis."""
        words = re.findall(r"[a-zA-Z]+(?:'[a-zA-Z]+)?", text.lower())
        word_set = set(words)
        num_words = len(words) if words else 1

        doc = self.nlp(text) if self.nlp else None

        formality = self._compute_formality(words, word_set, doc, num_words)
        sentiment = self._compute_sentiment(words, num_words)
        emotions = self._detect_emotions(words, num_words)
        objectivity = self._compute_objectivity(words, doc, num_words)
        persuasiveness = self._compute_persuasiveness(words, word_set, num_words)
        urgency = self._compute_urgency(words, word_set)
        professionalism = self._compute_professionalism(formality, sentiment, objectivity)

        return {
            "formality_score": round(formality, 4),
            "sentiment": sentiment,
            "emotions": emotions,
            "objectivity_score": round(objectivity, 4),
            "persuasiveness_score": round(persuasiveness, 4),
            "urgency_level": urgency,
            "professional_casual_score": round(professionalism, 4),
        }

    # ------------------------------------------------------------------
    # Formality (0 = very casual, 1 = very formal)
    # ------------------------------------------------------------------
    def _compute_formality(self, words: List[str], word_set: set, doc, num_words: int) -> float:
        score = 0.5  # baseline

        # POS-based formality: nouns, prepositions, articles boost formality;
        # pronouns, adverbs, interjections reduce it.
        if doc is not None:
            pos_counts: Dict[str, int] = {}
            for token in doc:
                pos_counts[token.pos_] = pos_counts.get(token.pos_, 0) + 1
            total_tokens = len(doc) or 1

            formal_pos = (
                pos_counts.get("NOUN", 0) + pos_counts.get("ADP", 0) + pos_counts.get("DET", 0)
            )
            informal_pos = (
                pos_counts.get("PRON", 0) + pos_counts.get("ADV", 0) + pos_counts.get("INTJ", 0)
            )

            pos_ratio = (formal_pos - informal_pos) / total_tokens
            score += pos_ratio * 0.3

        # Formal vocabulary markers
        formal_count = sum(1 for w in words if w in _FORMAL_MARKERS)
        score += min(0.2, formal_count / num_words * 5)

        # Contractions reduce formality
        contraction_count = sum(1 for w in words if w in _CONTRACTIONS)
        score -= min(0.25, contraction_count / num_words * 5)

        # Average word length: longer words tend to be more formal
        avg_len = sum(len(w) for w in words) / num_words
        if avg_len > 6:
            score += 0.1
        elif avg_len < 4:
            score -= 0.1

        return max(0.0, min(1.0, score))

    # ------------------------------------------------------------------
    # Sentiment
    # ------------------------------------------------------------------
    def _compute_sentiment(self, words: List[str], num_words: int) -> Dict[str, Any]:
        pos_count = sum(1 for w in words if w in _POSITIVE_WORDS)
        neg_count = sum(1 for w in words if w in _NEGATIVE_WORDS)
        total_sentiment_words = pos_count + neg_count

        if total_sentiment_words == 0:
            return {"label": "neutral", "score": 0.0, "positive_count": 0, "negative_count": 0}

        raw_score = (pos_count - neg_count) / num_words
        # Normalize to -1..1
        score = max(-1.0, min(1.0, raw_score * 10))

        if score > 0.1:
            label = "positive"
        elif score < -0.1:
            label = "negative"
        else:
            label = "neutral"

        return {
            "label": label,
            "score": round(score, 4),
            "positive_count": pos_count,
            "negative_count": neg_count,
        }

    # ------------------------------------------------------------------
    # Emotional tone detection
    # ------------------------------------------------------------------
    def _detect_emotions(self, words: List[str], num_words: int) -> Dict[str, float]:
        emotion_dicts = {
            "confident": _CONFIDENT_WORDS,
            "tentative": _TENTATIVE_WORDS,
            "analytical": _ANALYTICAL_WORDS,
            "joyful": _JOYFUL_WORDS,
            "angry": _ANGRY_WORDS,
            "sad": _SAD_WORDS,
        }
        result = {}
        for emotion, word_set in emotion_dicts.items():
            count = sum(1 for w in words if w in word_set)
            # Score 0-1 scaled
            result[emotion] = round(min(1.0, count / max(1, num_words) * 20), 4)
        return result

    # ------------------------------------------------------------------
    # Objectivity vs subjectivity (0 = subjective, 1 = objective)
    # ------------------------------------------------------------------
    def _compute_objectivity(self, words: List[str], doc, num_words: int) -> float:
        score = 0.5

        # First person pronouns indicate subjectivity
        first_person = {"i", "me", "my", "mine", "myself", "we", "us", "our", "ours"}
        fp_count = sum(1 for w in words if w in first_person)
        score -= min(0.3, fp_count / num_words * 5)

        # Opinion words reduce objectivity
        opinion_markers = {
            "think",
            "believe",
            "feel",
            "opinion",
            "personally",
            "honestly",
            "frankly",
            "obviously",
            "clearly",
            "surely",
            "love",
            "hate",
        }
        opinion_count = sum(1 for w in words if w in opinion_markers)
        score -= min(0.2, opinion_count / num_words * 5)

        # Analytical / data words increase objectivity
        data_words = {
            "data",
            "study",
            "research",
            "evidence",
            "finding",
            "result",
            "statistic",
            "percent",
            "analysis",
            "report",
            "survey",
            "measure",
        }
        data_count = sum(1 for w in words if w in data_words)
        score += min(0.2, data_count / num_words * 5)

        # Adjectives and adverbs reduce objectivity if spaCy available
        if doc is not None:
            adj_adv = sum(1 for t in doc if t.pos_ in ("ADJ", "ADV"))
            total = len(doc) or 1
            adj_ratio = adj_adv / total
            if adj_ratio > 0.15:
                score -= 0.1

        return max(0.0, min(1.0, score))

    # ------------------------------------------------------------------
    # Persuasiveness
    # ------------------------------------------------------------------
    def _compute_persuasiveness(self, words: List[str], word_set: set, num_words: int) -> float:
        score = 0.0

        persuasive_markers = {
            "you",
            "your",
            "imagine",
            "discover",
            "proven",
            "guarantee",
            "free",
            "new",
            "exclusive",
            "limited",
            "save",
            "best",
            "easy",
            "instantly",
            "secret",
            "powerful",
            "incredible",
            "amazing",
            "revolutionary",
            "transform",
            "boost",
            "unlock",
            "must",
            "should",
            "need",
            "act",
            "join",
            "because",
            "results",
        }
        p_count = sum(1 for w in words if w in persuasive_markers)
        score += min(0.5, p_count / num_words * 10)

        # Rhetorical questions
        question_count = len(re.findall(r"\?", " ".join(words)))
        score += min(0.15, question_count * 0.05)

        # Imperative verbs (rough heuristic: sentence-initial verbs)
        score += min(0.15, sum(1 for w in word_set & _URGENT_WORDS) / num_words * 5)

        # Repetition / emphasis
        exclamation_count = len(re.findall(r"!", " ".join(words)))
        score += min(0.1, exclamation_count * 0.03)

        return max(0.0, min(1.0, score))

    # ------------------------------------------------------------------
    # Urgency level
    # ------------------------------------------------------------------
    def _compute_urgency(self, words: List[str], word_set: set) -> Dict[str, Any]:
        count = sum(1 for w in words if w in _URGENT_WORDS)
        num_words = len(words) or 1
        ratio = count / num_words

        if ratio > 0.03:
            level = "high"
        elif ratio > 0.01:
            level = "medium"
        else:
            level = "low"

        return {"level": level, "score": round(min(1.0, ratio * 30), 4), "urgent_word_count": count}

    # ------------------------------------------------------------------
    # Professional/casual meter (0 = casual, 1 = professional)
    # ------------------------------------------------------------------
    @staticmethod
    def _compute_professionalism(
        formality: float, sentiment: Dict[str, Any], objectivity: float
    ) -> float:
        # Weighted combination
        score = formality * 0.4 + objectivity * 0.4
        # Extreme sentiment is less professional
        sent_abs = abs(sentiment.get("score", 0))
        score -= sent_abs * 0.2
        return max(0.0, min(1.0, score))
