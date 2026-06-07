"""
Lexical humanizer -- replaces AI-typical vocabulary with natural alternatives,
injects contractions, and rewrites common AI phrase patterns.
"""

import logging
import random
import re
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1. AI buzzword -> natural alternative mapping  (200+ entries)
# ---------------------------------------------------------------------------
BUZZWORD_REPLACEMENTS: Dict[str, List[str]] = {
    # Over-used hedging / formality
    "utilize": ["use", "work with"],
    "utilizes": ["uses", "works with"],
    "utilizing": ["using", "working with"],
    "utilization": ["use"],
    "leverage": ["use", "tap into", "draw on"],
    "leveraging": ["using", "drawing on"],
    "leveraged": ["used", "drew on"],
    "facilitate": ["help", "make easier", "support"],
    "facilitates": ["helps", "supports"],
    "facilitating": ["helping", "supporting"],
    "implement": ["set up", "put in place", "carry out"],
    "implements": ["sets up", "carries out"],
    "implementing": ["setting up", "carrying out"],
    "implementation": ["setup", "rollout"],
    "optimize": ["improve", "fine-tune", "streamline"],
    "optimizes": ["improves", "streamlines"],
    "optimizing": ["improving", "streamlining"],
    "optimization": ["improvement", "tuning"],
    "enhance": ["improve", "boost", "strengthen"],
    "enhances": ["improves", "boosts"],
    "enhancing": ["improving", "boosting"],
    "enhancement": ["improvement", "upgrade"],
    "enhancements": ["improvements", "upgrades"],
    "comprehensive": ["thorough", "complete", "full"],
    "comprehensively": ["thoroughly", "fully"],
    "delve": ["dig into", "look into", "explore"],
    "delves": ["digs into", "explores"],
    "delving": ["digging into", "exploring"],
    "crucial": ["important", "key", "vital"],
    "pivotal": ["key", "central", "important"],
    "paramount": ["very important", "essential"],
    "fundamental": ["basic", "core", "central"],
    "fundamentally": ["basically", "at its core"],
    "multifaceted": ["complex", "many-sided"],
    "intricate": ["complex", "detailed"],
    "intricacies": ["details", "complexities"],
    "nuanced": ["subtle", "detailed"],
    "nuances": ["subtleties", "fine points"],
    "moreover": ["also", "on top of that", "besides"],
    "furthermore": ["also", "what is more", "plus"],
    "additionally": ["also", "on top of that"],
    "consequently": ["so", "as a result"],
    "subsequently": ["then", "after that", "later"],
    "nevertheless": ["still", "even so", "yet"],
    "nonetheless": ["still", "even so"],
    "henceforth": ["from now on"],
    "thereby": ["in doing so", "by that"],
    "wherein": ["where", "in which"],
    "thereof": ["of that", "of it"],
    "aforementioned": ["mentioned earlier", "noted above"],
    "underscore": ["highlight", "stress", "point out"],
    "underscores": ["highlights", "stresses"],
    "underscoring": ["highlighting", "stressing"],
    "elucidate": ["explain", "clarify"],
    "elucidates": ["explains", "clarifies"],
    "elucidating": ["explaining", "clarifying"],
    "endeavor": ["try", "effort", "attempt"],
    "endeavors": ["tries", "efforts"],
    "commenced": ["started", "began"],
    "commence": ["start", "begin"],
    "commencing": ["starting", "beginning"],
    "terminate": ["end", "stop"],
    "terminated": ["ended", "stopped"],
    "termination": ["end", "ending"],
    "ascertain": ["find out", "determine"],
    "ascertained": ["found out", "determined"],
    "ameliorate": ["improve", "make better"],
    "ameliorating": ["improving"],
    "paradigm": ["model", "framework", "approach"],
    "paradigms": ["models", "frameworks"],
    "paradigm shift": ["major change", "turning point"],
    "synergy": ["teamwork", "combined effort"],
    "synergies": ["combined efforts"],
    "holistic": ["overall", "whole", "complete"],
    "holistically": ["as a whole", "overall"],
    "robust": ["strong", "solid", "reliable"],
    "robustly": ["strongly", "reliably"],
    "seamless": ["smooth", "effortless"],
    "seamlessly": ["smoothly", "effortlessly"],
    "meticulous": ["careful", "thorough", "precise"],
    "meticulously": ["carefully", "thoroughly"],
    "groundbreaking": ["innovative", "new", "pioneering"],
    "cutting-edge": ["latest", "advanced", "modern"],
    "state-of-the-art": ["latest", "most advanced", "modern"],
    "innovative": ["new", "creative", "original"],
    "revolutionize": ["transform", "change dramatically"],
    "revolutionizing": ["transforming", "reshaping"],
    "transformative": ["game-changing", "powerful"],
    "unprecedented": ["never seen before", "first-ever", "unheard-of"],
    "remarkable": ["notable", "striking", "impressive"],
    "remarkably": ["notably", "strikingly"],
    "notable": ["worth noting", "significant"],
    "notably": ["especially", "in particular"],
    "significant": ["important", "major", "big"],
    "significantly": ["greatly", "a lot", "by a wide margin"],
    "substantially": ["a lot", "greatly", "considerably"],
    "considerable": ["large", "sizable"],
    "considerably": ["a lot", "quite a bit"],
    "plethora": ["lot", "wide range", "many"],
    "myriad": ["many", "countless", "a wide range of"],
    "diverse": ["varied", "wide-ranging"],
    "diversity": ["variety", "range"],
    "inherent": ["built-in", "natural", "basic"],
    "inherently": ["by nature", "naturally"],
    "intrinsic": ["built-in", "natural", "core"],
    "intrinsically": ["by nature", "at its core"],
    "pertinent": ["relevant", "related"],
    "exacerbate": ["worsen", "make worse"],
    "exacerbated": ["worsened", "made worse"],
    "exacerbating": ["worsening", "making worse"],
    "mitigate": ["reduce", "lessen", "ease"],
    "mitigates": ["reduces", "lessens"],
    "mitigating": ["reducing", "easing"],
    "mitigation": ["reduction", "relief"],
    "alleviate": ["ease", "relieve", "reduce"],
    "alleviates": ["eases", "relieves"],
    "alleviating": ["easing", "relieving"],
    "propensity": ["tendency", "inclination"],
    "predicated": ["based", "founded"],
    "predicated on": ["based on", "built on"],
    "juxtaposition": ["contrast", "comparison"],
    "dichotomy": ["divide", "split", "contrast"],
    "epitome": ["perfect example", "model"],
    "epitomize": ["represent", "embody"],
    "epitomizes": ["represents", "embodies"],
    "proliferation": ["spread", "growth", "increase"],
    "burgeoning": ["growing", "expanding", "booming"],
    "ubiquitous": ["everywhere", "widespread", "common"],
    "indispensable": ["essential", "necessary", "vital"],
    "imperative": ["essential", "crucial", "necessary"],
    "necessitate": ["require", "call for"],
    "necessitates": ["requires", "calls for"],
    "cognizant": ["aware", "mindful"],
    "conducive": ["helpful", "good for", "favorable"],
    "discern": ["tell apart", "spot", "notice"],
    "discerning": ["sharp", "perceptive"],
    "encompass": ["include", "cover"],
    "encompasses": ["includes", "covers"],
    "encompassing": ["including", "covering"],
    "efficacy": ["effectiveness"],
    "efficacious": ["effective"],
    "expedite": ["speed up", "hasten"],
    "expediting": ["speeding up"],
    "foster": ["encourage", "promote", "nurture"],
    "fosters": ["encourages", "promotes"],
    "fostering": ["encouraging", "promoting"],
    "garner": ["gain", "earn", "attract"],
    "garners": ["gains", "earns"],
    "garnered": ["gained", "earned"],
    "harbinger": ["sign", "signal", "forerunner"],
    "impetus": ["push", "motivation", "spark"],
    "inception": ["start", "beginning"],
    "landscape": ["field", "scene", "area"],
    "manifestation": ["sign", "expression", "example"],
    "navigate": ["find your way through", "work through", "handle"],
    "navigating": ["working through", "handling"],
    "perpetuate": ["keep going", "continue", "maintain"],
    "perpetuates": ["keeps going", "continues"],
    "perpetuating": ["keeping alive", "continuing"],
    "precipitate": ["cause", "trigger", "bring about"],
    "proliferate": ["spread", "multiply", "grow"],
    "proliferates": ["spreads", "multiplies"],
    "quintessential": ["classic", "typical", "perfect"],
    "ramifications": ["consequences", "effects", "results"],
    "realm": ["area", "field", "domain"],
    "resonate": ["connect", "strike a chord"],
    "resonates": ["connects", "strikes a chord"],
    "salient": ["important", "key", "main"],
    "scrutinize": ["examine", "look closely at"],
    "scrutinizing": ["examining", "looking closely at"],
    "steadfast": ["firm", "unwavering", "committed"],
    "tangible": ["real", "concrete", "actual"],
    "testament": ["proof", "evidence"],
    "trajectory": ["path", "direction", "course"],
    "underpin": ["support", "form the basis of"],
    "underpins": ["supports", "is the basis of"],
    "underpinning": ["supporting", "underlying"],
    "vis-a-vis": ["compared to", "regarding", "about"],
    "whilst": ["while"],
    "amidst": ["amid", "in the middle of"],
    "amongst": ["among"],
    "hitherto": ["until now", "so far"],
    "inasmuch": ["since", "because"],
    "notwithstanding": ["despite", "in spite of"],
    "overarching": ["main", "overall", "broad"],
    "plausible": ["possible", "reasonable", "believable"],
    "bolster": ["strengthen", "support", "boost"],
    "bolsters": ["strengthens", "supports"],
    "bolstering": ["strengthening", "supporting"],
    "catapult": ["launch", "propel", "push"],
    "culminate": ["end up", "lead to", "result in"],
    "culminates": ["ends up", "leads to"],
    "delineate": ["outline", "describe", "map out"],
    "delineates": ["outlines", "describes"],
    "embark": ["start", "begin", "set out"],
    "embarking": ["starting", "setting out"],
    "in conclusion": ["to wrap up", "all in all"],
    "it is worth noting": ["note that", "keep in mind"],
    "it is important to note": ["keep in mind", "note that"],
    "in the realm of": ["in"],
    "in today's world": ["today", "these days", "now"],
    "tapestry": ["mix", "blend", "fabric"],
}

# ---------------------------------------------------------------------------
# 2. Contraction mappings  (applied with ~70% probability per hit)
# ---------------------------------------------------------------------------
CONTRACTION_MAP: Dict[str, str] = {
    "do not": "don't",
    "does not": "doesn't",
    "did not": "didn't",
    "will not": "won't",
    "would not": "wouldn't",
    "could not": "couldn't",
    "should not": "shouldn't",
    "can not": "can't",
    "cannot": "can't",
    "is not": "isn't",
    "are not": "aren't",
    "was not": "wasn't",
    "were not": "weren't",
    "has not": "hasn't",
    "have not": "haven't",
    "had not": "hadn't",
    "it is": "it's",
    "it has": "it's",
    "that is": "that's",
    "there is": "there's",
    "there are": "there're",
    "we are": "we're",
    "they are": "they're",
    "you are": "you're",
    "I am": "I'm",
    "I have": "I've",
    "I will": "I'll",
    "I would": "I'd",
    "we have": "we've",
    "we will": "we'll",
    "we would": "we'd",
    "they have": "they've",
    "they will": "they'll",
    "they would": "they'd",
    "you have": "you've",
    "you will": "you'll",
    "you would": "you'd",
    "he is": "he's",
    "she is": "she's",
    "he will": "he'll",
    "she will": "she'll",
    "he would": "he'd",
    "she would": "she'd",
    "who is": "who's",
    "who will": "who'll",
    "what is": "what's",
    "what will": "what'll",
    "let us": "let's",
}

# ---------------------------------------------------------------------------
# 3. AI phrase patterns  (15+ regex-based replacements)
# ---------------------------------------------------------------------------
AI_PHRASE_PATTERNS: List[Tuple[str, List[str]]] = [
    (
        r"\bIn today'?s (?:rapidly )?(?:evolving|changing) (?:world|landscape|era)\b",
        ["Today", "These days", "Right now"],
    ),
    (
        r"\bIt is (?:important|essential|crucial|vital) to (?:note|understand|recognize) that\b",
        ["Note that", "Keep in mind that", "Remember that"],
    ),
    (
        r"\bThis (?:article|essay|paper|piece) (?:will )?(?:explore|delve into|examine)s?\b",
        ["This looks at", "Here we cover", "Let's look at"],
    ),
    (
        r"\bIn (?:the )?light of (?:the )?(?:above|foregoing|this)\b",
        ["Given this", "With that in mind", "Considering this"],
    ),
    (r"\bAs (?:we )?(?:can )?(?:see|observe|note),?\b", ["Clearly", "As shown", "Evidently"]),
    (
        r"\bIt (?:is|has been) widely (?:acknowledged|recognized|accepted) that\b",
        ["Most people agree that", "It's generally known that"],
    ),
    (
        r"\bIn (?:order )?to (?:fully )?(?:understand|comprehend|grasp)\b",
        ["To understand", "To get", "To make sense of"],
    ),
    (
        r"\bPlays a (?:crucial|vital|pivotal|key|significant|important) role in\b",
        ["matters for", "helps with", "is key to"],
    ),
    (r"\bServes as a (?:testament|reminder|beacon|catalyst)\b", ["shows", "reminds us", "proves"]),
    (
        r"\bAt the (?:end of the day|heart of (?:the matter|it all))\b",
        ["Ultimately", "In the end", "When it comes down to it"],
    ),
    (r"\bIt goes without saying that\b", ["Obviously", "Clearly", "Of course"]),
    (
        r"\bA (?:wide )?(?:variety|range|plethora|myriad) of\b",
        ["Many", "Lots of", "All sorts of", "Various"],
    ),
    (r"\bIn (?:this|the) (?:regard|respect|context)\b", ["Here", "On this point", "About this"]),
    (r"\bTo (?:sum|wrap) (?:it )?up\b", ["Overall", "All in all", "In short"]),
    (r"\bOn the other hand\b", ["Then again", "But", "However"]),
    (r"\bBy and large\b", ["Mostly", "Generally", "For the most part"]),
    (
        r"\bFrom (?:a|the) (?:\w+ )?(?:perspective|standpoint|viewpoint)\b",
        ["Looking at it this way", "Seen this way"],
    ),
    (r"\bHaving said that\b", ["That said", "Still", "Even so"]),
]


class LexicalHumanizer:
    """
    Apply lexical-level transformations to reduce AI-typical word choices
    and inject more natural, human-sounding language patterns.
    """

    def __init__(
        self,
        contraction_probability: float = 0.70,
        seed: int | None = None,
    ) -> None:
        self.contraction_probability = contraction_probability
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def humanize(self, text: str) -> str:
        """
        Run the full lexical humanization pipeline on *text* and return the
        transformed string.
        """
        text = self._replace_ai_phrases(text)
        text = self._replace_buzzwords(text)
        text = self._inject_contractions(text)
        return text

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _replace_buzzwords(self, text: str) -> str:
        # Sort by length descending so longer phrases match first
        for buzzword in sorted(BUZZWORD_REPLACEMENTS, key=len, reverse=True):
            pattern = re.compile(re.escape(buzzword), re.IGNORECASE)

            def _repl(m: re.Match, bw: str = buzzword) -> str:
                alts = BUZZWORD_REPLACEMENTS[bw]
                replacement = self._rng.choice(alts)
                # Preserve original capitalisation style
                if m.group(0)[0].isupper():
                    replacement = replacement[0].upper() + replacement[1:]
                return replacement

            text = pattern.sub(_repl, text)
        return text

    def _inject_contractions(self, text: str) -> str:
        for full_form, contracted in CONTRACTION_MAP.items():
            if self._rng.random() > self.contraction_probability:
                continue
            pattern = re.compile(re.escape(full_form), re.IGNORECASE)

            def _repl(m: re.Match, c: str = contracted) -> str:
                if m.group(0)[0].isupper():
                    return c[0].upper() + c[1:]
                return c

            text = pattern.sub(_repl, text)
        return text

    def _replace_ai_phrases(self, text: str) -> str:
        for pattern_str, replacements in AI_PHRASE_PATTERNS:
            pattern = re.compile(pattern_str, re.IGNORECASE)

            def _repl(m: re.Match, alts: List[str] = replacements) -> str:
                return self._rng.choice(alts)

            text = pattern.sub(_repl, text)
        return text
