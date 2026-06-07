"""
ClarityAI Detection Signals.

All detectors inherit from BaseDetector and expose an async ``analyze(text)``
method that returns a standardised result dict.
"""

from app.ml.detectors.base import BaseDetector
from app.ml.detectors.perplexity_burstiness import PerplexityBurstinessDetector
from app.ml.detectors.fast_detectgpt import FastDetectGPTDetector
from app.ml.detectors.binoculars import BinocularsDetector
from app.ml.detectors.ghostbuster import GhostbusterDetector
from app.ml.detectors.watermark import WatermarkDetector
from app.ml.detectors.gltr import GLTRDetector
from app.ml.detectors.stylometric import StylometricDetector
from app.ml.detectors.entropy_analyzer import EntropyAnalyzerDetector
from app.ml.detectors.zero_shot_ensemble import ZeroShotEnsembleDetector
from app.ml.detectors.coherence import CoherenceDetector
from app.ml.detectors.vocabulary_richness import VocabularyRichnessDetector
from app.ml.detectors.pos_patterns import POSPatternsDetector
from app.ml.detectors.repetition import RepetitionDetector
from app.ml.detectors.ai_fingerprint import AIFingerprintDetector
from app.ml.detectors.sentence_level import SentenceLevelDetector
from app.ml.detectors.ai_pattern_database import AIPatternDatabaseDetector
from app.ml.detectors.cross_reference import CrossReferenceDetector
from app.ml.detectors.multi_model_consensus import MultiModelConsensusDetector
from app.ml.detectors.rewrite_detector import RewriteDetector

__all__ = [
    "BaseDetector",
    "PerplexityBurstinessDetector",
    "FastDetectGPTDetector",
    "BinocularsDetector",
    "GhostbusterDetector",
    "WatermarkDetector",
    "GLTRDetector",
    "StylometricDetector",
    "EntropyAnalyzerDetector",
    "ZeroShotEnsembleDetector",
    "CoherenceDetector",
    "VocabularyRichnessDetector",
    "POSPatternsDetector",
    "RepetitionDetector",
    "AIFingerprintDetector",
    "SentenceLevelDetector",
    "AIPatternDatabaseDetector",
    "CrossReferenceDetector",
    "MultiModelConsensusDetector",
    "RewriteDetector",
]
