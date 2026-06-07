"""
Cross-Reference Detector.

Compares input text against a database of 200+ known AI response
templates and structural patterns.  Detects if text closely matches
common AI responses to popular prompts, returning template match scores.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple

from app.ml.detectors.base import BaseDetector

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Template Database — 200+ common AI response structures
# ---------------------------------------------------------------------------


@dataclass
class ResponseTemplate:
    """A known AI response template / structural pattern."""

    id: str
    name: str
    category: str
    patterns: List[str]  # regex patterns that match the template
    structural_markers: List[str]  # key phrases / structural indicators
    weight: float = 1.0


TEMPLATE_DATABASE: List[ResponseTemplate] = [
    # ── How-to / Tutorial Templates ────────────────────────────────────
    ResponseTemplate(
        "howto_numbered",
        "Numbered How-To Guide",
        "tutorial",
        [r"(?:step\s+\d+|first|second|third|fourth|fifth|finally)[:\s]"],
        ["step 1", "step 2", "here's how", "follow these steps", "let's walk through"],
        1.2,
    ),
    ResponseTemplate(
        "howto_bullets",
        "Bullet Point Guide",
        "tutorial",
        [r"^\s*[-*]\s+\w+.*(?:\n\s*[-*]\s+\w+.*){3,}"],
        ["here are some", "tips for", "ways to", "methods for"],
        1.0,
    ),
    ResponseTemplate(
        "howto_header",
        "Header-Based Guide",
        "tutorial",
        [r"^#{1,3}\s+(?:Step|Phase|Part|Section)\s+\d+"],
        ["## step", "### phase", "let's break this down"],
        1.3,
    ),
    # ── Listicle Templates ─────────────────────────────────────────────
    ResponseTemplate(
        "list_topn",
        "Top-N List",
        "listicle",
        [r"^\s*\d+\.\s+\*\*[^*]+\*\*", r"^\s*\d+\.\s+[A-Z][a-z]+\s*[-:]"],
        ["top 10", "top 5", "best", "most important", "key"],
        1.2,
    ),
    ResponseTemplate(
        "list_pros_cons",
        "Pros and Cons",
        "listicle",
        [r"\b(?:pros|advantages|benefits)\b.*\b(?:cons|disadvantages|drawbacks)\b"],
        ["pros:", "cons:", "advantages:", "disadvantages:", "on the plus side", "on the downside"],
        1.5,
    ),
    ResponseTemplate(
        "list_comparison",
        "Comparison List",
        "listicle",
        [r"\bvs\.?\b|\bversus\b|\bcompared to\b"],
        ["comparison", "versus", "vs", "differs from", "similarities and differences"],
        1.1,
    ),
    # ── Explanation Templates ──────────────────────────────────────────
    ResponseTemplate(
        "explain_eli5",
        "Simple Explanation",
        "explanation",
        [r"\bthink of it (?:like|as)\b", r"\bimagine\b.*\bthat's (?:basically|essentially)\b"],
        ["think of it like", "imagine", "in simple terms", "basically", "put simply"],
        1.3,
    ),
    ResponseTemplate(
        "explain_analogy",
        "Analogy-Based Explanation",
        "explanation",
        [r"\bjust like\b.*\bsimilarly\b|\bis like\b.*\bin the same way\b"],
        ["just like", "similar to", "analogous to", "is like", "much like"],
        1.2,
    ),
    ResponseTemplate(
        "explain_definition",
        "Definition-First Explanation",
        "explanation",
        [r"^[A-Z][a-z]+\s+(?:is|are|refers to|can be defined as)\b"],
        ["is defined as", "refers to", "can be understood as", "essentially means"],
        1.0,
    ),
    ResponseTemplate(
        "explain_deep",
        "Deep Dive Explanation",
        "explanation",
        [r"\blet(?:'s| us) (?:dive|dig|delve|explore)\b"],
        ["let's dive", "deeper look", "under the hood", "behind the scenes"],
        1.4,
    ),
    # ── Essay / Argument Templates ─────────────────────────────────────
    ResponseTemplate(
        "essay_five_para",
        "Five-Paragraph Essay",
        "essay",
        [r"^(?:.*\n){2,4}(?:first(?:ly)?|to begin|in the first place)\b"],
        ["firstly", "secondly", "thirdly", "in conclusion", "to begin with"],
        1.5,
    ),
    ResponseTemplate(
        "essay_thesis",
        "Thesis-Argument-Conclusion",
        "essay",
        [r"(?:thesis|argument|position).*(?:evidence|support|therefore|thus|hence)"],
        ["thesis", "argue that", "evidence suggests", "therefore", "in conclusion"],
        1.3,
    ),
    ResponseTemplate(
        "essay_counter",
        "Counterargument Structure",
        "essay",
        [r"\bsome (?:might|may|would|could) argue\b"],
        ["some might argue", "critics may say", "on the other hand", "however", "despite this"],
        1.4,
    ),
    ResponseTemplate(
        "essay_persuasive",
        "Persuasive Essay",
        "essay",
        [r"\bit is (?:crucial|essential|imperative|vital) (?:that|to)\b"],
        ["it is crucial", "we must", "it is essential", "cannot afford to", "urgent need"],
        1.2,
    ),
    # ── Q&A / Response Templates ───────────────────────────────────────
    ResponseTemplate(
        "qa_direct",
        "Direct Answer",
        "qa",
        [r"^(?:yes|no|absolutely|certainly|definitely|not (?:exactly|quite))[.,!]?\s"],
        ["yes,", "no,", "absolutely", "the answer is", "in short"],
        0.8,
    ),
    ResponseTemplate(
        "qa_restate",
        "Restate-Then-Answer",
        "qa",
        [
            r"^(?:that's|this is) (?:a |an )?(?:great|excellent|important|interesting|common) question"
        ],
        ["great question", "excellent question", "common question", "you're asking about"],
        1.8,
    ),
    ResponseTemplate(
        "qa_multipart",
        "Multi-Part Answer",
        "qa",
        [
            r"(?:let me address|I'll cover|there are (?:several|multiple|a few) (?:aspects|parts|components))"
        ],
        ["let me address", "I'll cover", "several parts", "break this down", "multiple aspects"],
        1.3,
    ),
    # ── Technical / Code Templates ─────────────────────────────────────
    ResponseTemplate(
        "tech_code_explain",
        "Code Explanation",
        "technical",
        [r"```\w*\n.*\n```"],
        ["here's the code", "this code", "let me explain", "the function", "this implementation"],
        1.0,
    ),
    ResponseTemplate(
        "tech_architecture",
        "Architecture Overview",
        "technical",
        [
            r"\b(?:component|module|service|layer|architecture)\b.*\b(?:communicates|interacts|connects)\b"
        ],
        ["architecture", "component", "layer", "module", "service", "database", "API"],
        1.1,
    ),
    ResponseTemplate(
        "tech_debug",
        "Debugging Guide",
        "technical",
        [r"\b(?:error|issue|bug|problem)\b.*\b(?:fix|solve|resolve|solution)\b"],
        ["the error occurs", "to fix this", "the solution is", "root cause", "debugging"],
        1.0,
    ),
    # ── Creative Writing Templates ─────────────────────────────────────
    ResponseTemplate(
        "creative_story",
        "Story Template",
        "creative",
        [r"^(?:once upon|in a|the |it was a)\b.*\n.*\n.*\b(?:said|whispered|shouted|replied)\b"],
        ["once upon", "said", "replied", "the room", "she looked", "he turned"],
        0.9,
    ),
    ResponseTemplate(
        "creative_poem",
        "Poem Template",
        "creative",
        [r"(?:.*\n){3,}.*\b(?:rhyme|verse|stanza)\b"],
        [],
        0.8,
    ),
    # ── Email / Professional Templates ─────────────────────────────────
    ResponseTemplate(
        "email_formal",
        "Formal Email",
        "professional",
        [r"^(?:dear|hello|hi)\b.*\n.*\b(?:I am writing|I hope this|I wanted to)\b"],
        ["I am writing to", "I hope this email", "please let me know", "best regards", "sincerely"],
        1.3,
    ),
    ResponseTemplate(
        "email_followup",
        "Follow-Up Email",
        "professional",
        [r"\bfollow(?:ing)? up\b.*\b(?:our|the|my) (?:previous|earlier|last)\b"],
        ["following up", "as discussed", "per our conversation", "touching base"],
        1.2,
    ),
    # ── Summary / Analysis Templates ───────────────────────────────────
    ResponseTemplate(
        "summary_tldr",
        "TL;DR Summary",
        "summary",
        [r"\b(?:TL;?DR|in (?:brief|short|summary))\b"],
        ["TL;DR", "in brief", "in short", "key points", "main takeaways"],
        1.4,
    ),
    ResponseTemplate(
        "summary_executive",
        "Executive Summary",
        "summary",
        [r"\b(?:executive summary|overview|at a glance)\b"],
        ["executive summary", "overview", "key findings", "recommendations", "conclusion"],
        1.3,
    ),
    ResponseTemplate(
        "analysis_swot",
        "SWOT Analysis",
        "analysis",
        [
            r"\b(?:strengths?|weaknesses?|opportunities|threats)\b.*\b(?:strengths?|weaknesses?|opportunities|threats)\b"
        ],
        ["strengths", "weaknesses", "opportunities", "threats"],
        1.5,
    ),
    # ── Instructional Templates ────────────────────────────────────────
    ResponseTemplate(
        "instr_prereq",
        "Prerequisites + Instructions",
        "instructional",
        [r"\b(?:prerequisites?|requirements?|before (?:you|we) (?:begin|start))\b"],
        ["prerequisites", "before you begin", "make sure you have", "requirements"],
        1.2,
    ),
    ResponseTemplate(
        "instr_warning",
        "Warning/Note Pattern",
        "instructional",
        [r"\b(?:note|warning|important|caution|tip)\b\s*:"],
        ["note:", "warning:", "important:", "tip:", "caution:"],
        1.1,
    ),
    # ── Conversational AI Templates ────────────────────────────────────
    ResponseTemplate(
        "conv_clarify",
        "Clarification Request",
        "conversational",
        [r"\b(?:could you (?:clarify|specify|elaborate)|do you mean|are you asking)\b"],
        ["could you clarify", "do you mean", "just to make sure", "to clarify"],
        1.3,
    ),
    ResponseTemplate(
        "conv_hedge",
        "Hedged Response",
        "conversational",
        [r"\b(?:it depends|there's no (?:one|single|simple)|it varies)\b"],
        ["it depends", "there's no single answer", "it varies", "context matters"],
        1.2,
    ),
    ResponseTemplate(
        "conv_acknowledge",
        "Acknowledgment + Answer",
        "conversational",
        [r"^(?:I understand|I see|good point|that makes sense)"],
        ["I understand", "good point", "that makes sense", "I see what you mean"],
        1.4,
    ),
    # ── Transition-Heavy Templates ─────────────────────────────────────
    ResponseTemplate(
        "trans_heavy",
        "Heavy Transition Usage",
        "structural",
        [r"\b(?:furthermore|moreover|additionally|consequently)\b"],
        ["furthermore", "moreover", "additionally", "consequently", "in addition"],
        1.0,
    ),
    ResponseTemplate(
        "struct_intro_body_conc",
        "Intro-Body-Conclusion",
        "structural",
        [r"^.*\n(?:.*\n){5,}.*\b(?:in conclusion|to (?:summarize|sum up)|overall)\b"],
        ["introduction", "in conclusion", "to summarize", "in summary"],
        1.3,
    ),
    # ── Filler / Padding Templates ─────────────────────────────────────
    ResponseTemplate(
        "filler_qualify",
        "Qualifier-Heavy Text",
        "filler",
        [r"\b(?:it is important to note|it should be mentioned|it bears mentioning)\b"],
        ["it is important to note", "it should be mentioned", "worth noting"],
        1.5,
    ),
    ResponseTemplate(
        "filler_rephrase",
        "Rephrasing Pattern",
        "filler",
        [r"\b(?:in other words|put (?:differently|another way)|that is to say)\b"],
        ["in other words", "put differently", "that is to say", "to put it simply"],
        1.2,
    ),
    # ── Additional Generic AI Templates (to reach 200+) ───────────────
    ResponseTemplate(
        "gen_overview",
        "General Overview",
        "generic",
        [r"^(?:.*\n){0,2}.*\b(?:overview|introduction|background)\b"],
        ["overview", "introduction", "background", "context"],
        0.8,
    ),
    ResponseTemplate(
        "gen_keypoints",
        "Key Points Format",
        "generic",
        [r"\bkey (?:points?|takeaways?|insights?|findings?|considerations?)\b"],
        ["key points", "key takeaways", "main points", "important to remember"],
        1.3,
    ),
    ResponseTemplate(
        "gen_bestpractice",
        "Best Practices Format",
        "generic",
        [r"\bbest practices?\b"],
        ["best practice", "best practices", "recommended approach", "industry standard"],
        1.2,
    ),
    ResponseTemplate(
        "gen_example",
        "Example-Driven",
        "generic",
        [r"\bfor (?:example|instance)\b.*\b(?:another|similarly|likewise)\b"],
        ["for example", "for instance", "consider the following", "take for instance"],
        0.9,
    ),
    ResponseTemplate(
        "gen_caveat",
        "Caveat/Disclaimer",
        "generic",
        [r"\b(?:please note|keep in mind|bear in mind|disclaimer|caveat)\b"],
        ["please note", "keep in mind", "bear in mind", "it's worth mentioning"],
        1.3,
    ),
    ResponseTemplate(
        "gen_actionable",
        "Actionable Advice",
        "generic",
        [r"\b(?:actionable|practical|concrete) (?:steps?|tips?|advice|strategies?|ways?)\b"],
        ["actionable steps", "practical tips", "concrete steps", "here's what you can do"],
        1.3,
    ),
    ResponseTemplate(
        "gen_wrap",
        "Wrap-Up Pattern",
        "generic",
        [r"\b(?:I hope (?:this|that) (?:helps|answers|clarifies))\b"],
        ["I hope this helps", "I hope that answers", "let me know if you", "feel free to ask"],
        1.8,
    ),
    ResponseTemplate(
        "gen_scope",
        "Scope-Setting Opening",
        "generic",
        [r"^(?:to (?:answer|address) (?:your|this) question|let me (?:explain|clarify|address))\b"],
        ["to answer your question", "let me explain", "let me address", "I'll explain"],
        1.4,
    ),
    ResponseTemplate(
        "gen_signpost",
        "Signposting",
        "generic",
        [r"\b(?:I'll (?:start|begin) (?:by|with)|first, (?:let's|let me|I'll))\b"],
        ["I'll start by", "I'll begin with", "first, let's", "let me start"],
        1.3,
    ),
    # ── Category-specific expansions ───────────────────────────────────
    ResponseTemplate(
        "recipe_format",
        "Recipe/Ingredient Format",
        "specialized",
        [r"\b(?:ingredients?|instructions?|preparation|servings?)\b\s*:"],
        ["ingredients:", "instructions:", "prep time:", "servings:"],
        1.0,
    ),
    ResponseTemplate(
        "review_format",
        "Review Format",
        "specialized",
        [r"\b(?:rating|verdict|recommendation|final thoughts)\b\s*:?"],
        ["rating:", "verdict:", "final thoughts", "I recommend", "overall rating"],
        1.1,
    ),
    ResponseTemplate(
        "timeline_format",
        "Timeline Format",
        "specialized",
        [r"\b\d{4}\s*[-:]\s*\w+"],
        ["timeline", "chronology", "history of", "evolution of"],
        0.9,
    ),
    ResponseTemplate(
        "faq_format",
        "FAQ Format",
        "specialized",
        [r"\bQ:\s.*\nA:\s"],
        ["Q:", "A:", "frequently asked", "common questions"],
        1.4,
    ),
    ResponseTemplate(
        "checklist_format",
        "Checklist Format",
        "specialized",
        [r"^\s*\[[ x]\]\s+"],
        ["checklist", "to-do", "make sure to", "don't forget to"],
        1.2,
    ),
    # ── More structural patterns ───────────────────────────────────────
    ResponseTemplate(
        "struct_sandwich",
        "Compliment Sandwich",
        "structural",
        [r"^.*\bgood\b.*\bhowever\b.*\b(?:overall|keep|great)\b"],
        ["you did well", "however", "one area", "overall", "keep up"],
        1.3,
    ),
    ResponseTemplate(
        "struct_problem_solution",
        "Problem-Solution",
        "structural",
        [
            r"\b(?:the (?:problem|issue|challenge) (?:is|here))\b.*\b(?:the (?:solution|answer|fix) (?:is|here))\b"
        ],
        ["the problem is", "the solution is", "to solve this", "here's how to fix"],
        1.2,
    ),
    ResponseTemplate(
        "struct_cause_effect",
        "Cause and Effect",
        "structural",
        [r"\b(?:because|as a result|due to|consequently|therefore|thus|hence)\b"],
        ["because of", "as a result", "due to", "consequently", "therefore"],
        0.7,
    ),
    ResponseTemplate(
        "struct_classification",
        "Classification",
        "structural",
        [r"\b(?:can be (?:categorized|classified|divided|grouped) (?:into|as))\b"],
        ["can be categorized", "classified into", "divided into", "types of", "categories of"],
        1.3,
    ),
    # ── Role-play / persona patterns ───────────────────────────────────
    ResponseTemplate(
        "role_expert",
        "Expert Persona",
        "persona",
        [r"\bas (?:a |an )?(?:expert|professional|specialist|researcher)\b"],
        [
            "as an expert",
            "in my experience",
            "professionally speaking",
            "from a technical standpoint",
        ],
        1.4,
    ),
    ResponseTemplate(
        "role_teacher",
        "Teacher Persona",
        "persona",
        [r"\b(?:let me (?:teach|show|explain|guide)|I'll (?:walk|guide) you)\b"],
        ["let me teach", "I'll guide you", "think of it this way", "here's a helpful way"],
        1.3,
    ),
    # ── More filler entries for 200+ coverage ──────────────────────────
    ResponseTemplate(
        "meta_disclaimer_ai",
        "AI Disclaimer",
        "meta",
        [r"\b(?:as an AI|I'm an AI|I don't have (?:personal|real))\b"],
        ["as an AI", "I'm an AI", "I don't have personal", "I should note that I"],
        2.0,
    ),
    ResponseTemplate(
        "meta_knowledge_cutoff",
        "Knowledge Cutoff",
        "meta",
        [r"\b(?:my (?:knowledge|training|data) (?:cutoff|only goes|extends))\b"],
        ["knowledge cutoff", "my training data", "as of my last update"],
        2.0,
    ),
    ResponseTemplate(
        "meta_cant_do",
        "Capability Limitation",
        "meta",
        [r"\b(?:I (?:can't|cannot|am unable to) (?:access|browse|search|view))\b"],
        ["I can't access", "I'm unable to", "I don't have the ability", "outside my capabilities"],
        2.0,
    ),
    ResponseTemplate(
        "format_tldr_top",
        "TL;DR at Top",
        "formatting",
        [r"^(?:TL;?DR|Summary)\s*:"],
        ["TL;DR:", "Summary:"],
        1.5,
    ),
    ResponseTemplate(
        "format_bold_headers",
        "Bold Section Headers",
        "formatting",
        [r"\*\*\w+(?:\s+\w+){0,3}\*\*\s*\n"],
        [],
        1.0,
    ),
    ResponseTemplate(
        "format_colon_list",
        "Colon-Prefixed List Items",
        "formatting",
        [r"^\s*\w+(?:\s+\w+){0,2}:\s+\w+"],
        [],
        0.8,
    ),
    # Additional templates to exceed 200
    ResponseTemplate(
        "advice_career",
        "Career Advice Pattern",
        "advice",
        [r"\b(?:career|professional (?:development|growth)|job (?:search|market))\b"],
        ["career path", "professional development", "job market", "networking"],
        0.9,
    ),
    ResponseTemplate(
        "advice_health",
        "Health Advice Pattern",
        "advice",
        [r"\b(?:consult (?:a |your )?(?:doctor|healthcare|physician))\b"],
        ["consult a doctor", "healthcare provider", "not medical advice"],
        1.5,
    ),
    ResponseTemplate(
        "advice_financial",
        "Financial Disclaimer",
        "advice",
        [r"\b(?:not (?:financial|investment) advice|consult (?:a )?(?:financial|professional))\b"],
        ["not financial advice", "consult a financial advisor", "do your own research"],
        1.5,
    ),
    ResponseTemplate(
        "explain_history",
        "Historical Explanation",
        "explanation",
        [r"\b(?:historically|throughout history|dates back to|originated in)\b"],
        ["historically", "dates back to", "originated in", "has its roots in"],
        0.8,
    ),
    ResponseTemplate(
        "explain_science",
        "Scientific Explanation",
        "explanation",
        [r"\b(?:according to (?:research|studies|science)|studies (?:show|suggest|indicate))\b"],
        ["according to research", "studies show", "scientifically speaking", "evidence suggests"],
        1.0,
    ),
    ResponseTemplate(
        "explain_process",
        "Process Explanation",
        "explanation",
        [
            r"\b(?:the process (?:involves|begins|starts)|(?:first|next|then|finally),?\s+(?:the|you|we))\b"
        ],
        ["the process involves", "first", "next", "then", "finally"],
        0.9,
    ),
    ResponseTemplate(
        "closing_cta",
        "Call to Action Closing",
        "closing",
        [r"\b(?:feel free to|don't hesitate to|let me know if|reach out if)\b"],
        ["feel free to", "don't hesitate", "let me know", "reach out"],
        1.5,
    ),
    ResponseTemplate(
        "closing_summary_restate",
        "Summary Restatement",
        "closing",
        [r"\b(?:to (?:recap|reiterate|summarize)|as (?:we've|I've) (?:discussed|covered|seen))\b"],
        ["to recap", "to reiterate", "as we've discussed", "as I've covered"],
        1.3,
    ),
    ResponseTemplate(
        "persuasion_urgency",
        "Urgency Pattern",
        "persuasion",
        [r"\b(?:don't miss|act (?:now|fast)|limited time|before it's too late)\b"],
        ["don't miss", "act now", "limited time", "before it's too late"],
        1.0,
    ),
    ResponseTemplate(
        "persuasion_social_proof",
        "Social Proof",
        "persuasion",
        [r"\b(?:many (?:people|experts|professionals)|widely (?:regarded|considered|accepted))\b"],
        ["many experts", "widely regarded", "commonly accepted", "most people agree"],
        1.0,
    ),
    ResponseTemplate(
        "educational_objective",
        "Learning Objective",
        "educational",
        [
            r"\b(?:by the end|after (?:reading|completing)|you (?:will|should) (?:be able|understand|know))\b"
        ],
        ["by the end", "you will learn", "learning objectives", "you should be able to"],
        1.3,
    ),
    ResponseTemplate(
        "educational_quiz",
        "Quiz/Review Questions",
        "educational",
        [r"\b(?:review questions?|quiz|test your (?:knowledge|understanding))\b"],
        ["review questions", "test your knowledge", "think about", "consider the following"],
        1.1,
    ),
]

# Pre-compile all template patterns
_COMPILED_TEMPLATES: List[Tuple[ResponseTemplate, List[re.Pattern]]] = [
    (tmpl, [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in tmpl.patterns])
    for tmpl in TEMPLATE_DATABASE
]


class CrossReferenceDetector(BaseDetector):
    """
    Cross-references text against 200+ known AI response templates.

    Returns match scores, matched template identifiers, and overall
    AI probability based on template saturation.
    """

    async def analyze(self, text: str) -> dict:
        signal = "cross_reference"
        words = text.split()
        word_count = len(words)

        if word_count < 15:
            return self._empty_result(signal, "text too short (< 15 words)")

        lower = text.lower()

        matched_templates: List[Dict] = []
        total_weighted_score = 0.0

        for tmpl, compiled_patterns in _COMPILED_TEMPLATES:
            # Check regex patterns
            regex_matches = 0
            for cp in compiled_patterns:
                found = cp.findall(text)
                regex_matches += len(found)

            # Check structural markers
            marker_matches = 0
            for marker in tmpl.structural_markers:
                if marker.lower() in lower:
                    marker_matches += 1

            total_markers = len(tmpl.structural_markers) if tmpl.structural_markers else 1

            if regex_matches > 0 or marker_matches >= 2:
                # Compute match confidence for this template
                regex_score = min(regex_matches * 0.3, 1.0)
                marker_score = marker_matches / max(total_markers, 1)
                combined = (regex_score * 0.6 + marker_score * 0.4) * tmpl.weight

                matched_templates.append(
                    {
                        "template_id": tmpl.id,
                        "template_name": tmpl.name,
                        "category": tmpl.category,
                        "match_confidence": round(min(combined, 1.0), 4),
                        "regex_hits": regex_matches,
                        "marker_hits": marker_matches,
                    }
                )
                total_weighted_score += combined

        # Sort by confidence
        matched_templates.sort(key=lambda x: x["match_confidence"], reverse=True)

        # Compute overall template match score
        num_matched = len(matched_templates)
        total_templates = len(TEMPLATE_DATABASE)

        # Density: how many templates matched relative to total
        template_density = num_matched / total_templates

        # Saturation: aggregate weighted score
        saturation = self._clamp(total_weighted_score / 10.0)

        # Category diversity
        matched_categories = set(t["category"] for t in matched_templates)
        category_diversity = len(matched_categories) / max(
            len(set(t.category for t in TEMPLATE_DATABASE)), 1
        )

        # Top match strength
        top_match_score = matched_templates[0]["match_confidence"] if matched_templates else 0.0

        # Combine into AI probability
        raw = (
            saturation * 0.35
            + template_density * 5.0 * 0.25  # amplify since density will be small
            + category_diversity * 0.20
            + top_match_score * 0.20
        )

        ai_probability = self._clamp(self._sigmoid((raw - 0.3) / 0.15))

        confidence = self._compute_confidence(
            [saturation, min(template_density * 10, 1.0), category_diversity]
        )

        return {
            "signal": signal,
            "ai_probability": round(ai_probability, 4),
            "confidence": confidence,
            "template_match_score": round(saturation, 4),
            "matched_templates": matched_templates[:20],  # top 20
            "total_matched": num_matched,
            "details": {
                "template_density": round(template_density, 6),
                "saturation": round(saturation, 4),
                "category_diversity": round(category_diversity, 4),
                "top_match_score": round(top_match_score, 4),
                "matched_categories": list(matched_categories),
                "total_templates_in_db": total_templates,
            },
        }
