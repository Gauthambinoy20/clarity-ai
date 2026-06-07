"""
Citation and reference extractor for ClarityAI.

Detects citation styles, extracts inline citations and reference lists,
validates format consistency, and cross-references.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Citation patterns for each style
# ---------------------------------------------------------------------------

# APA: (Author, Year) or (Author & Author, Year) or (Author et al., Year)
_APA_INLINE = re.compile(
    r"\(([A-Z][a-zA-Z\-]+(?:\s(?:&|and)\s[A-Z][a-zA-Z\-]+)?(?:\set\sal\.)?),?\s*(\d{4}[a-z]?)\)"
)
# APA reference: Author, A. B. (Year). Title. Source.
_APA_REFERENCE = re.compile(
    r"^([A-Z][a-zA-Z\-]+(?:,\s[A-Z]\.[\s\-]?)+(?:,?\s(?:&|and)\s[A-Z][a-zA-Z\-]+(?:,\s[A-Z]\.[\s\-]?)+)*)\s*\((\d{4}[a-z]?)\)\.\s*(.+?)(?:\.|$)",
    re.MULTILINE,
)

# MLA: (Author Page) or (Author)
_MLA_INLINE = re.compile(r"\(([A-Z][a-zA-Z\-]+(?:\sand\s[A-Z][a-zA-Z\-]+)?)\s+(\d{1,4})\)")

# IEEE: [1], [2], [1-3], [1, 2]
_IEEE_INLINE = re.compile(r"\[(\d+(?:\s*[-,]\s*\d+)*)\]")
# IEEE reference: [1] A. Author, "Title," ...
_IEEE_REFERENCE = re.compile(r"^\[(\d+)\]\s+(.+?)(?:\.|$)", re.MULTILINE)

# Chicago notes: superscript numbers (we look for patterns like ^1 or footnote markers)
_CHICAGO_INLINE = re.compile(r"(?:\^|¹|²|³|⁴|⁵|⁶|⁷|⁸|⁹|⁰|\[fn(\d+)\])(\d*)")

# Harvard: similar to APA but with slight variations (Author Year) without comma
_HARVARD_INLINE = re.compile(r"\(([A-Z][a-zA-Z\-]+(?:\sand\s[A-Z][a-zA-Z\-]+)?)\s+(\d{4}[a-z]?)\)")

# Generic reference list entry (numbered)
_NUMBERED_REFERENCE = re.compile(r"^\s*\[?(\d{1,3})\]?\s*\.?\s+(.+)", re.MULTILINE)

# Generic author-year reference
_AUTHOR_YEAR_REFERENCE = re.compile(r"^([A-Z][a-zA-Z\-]+.*?)\((\d{4}[a-z]?)\)", re.MULTILINE)


class CitationExtractor:
    """Extracts and validates citations from academic and professional text."""

    def analyze(self, text: str) -> Dict[str, Any]:
        """Run full citation extraction and validation."""
        inline_citations = self._extract_inline_citations(text)
        citation_style = self._detect_citation_style(text, inline_citations)
        references = self._extract_references(text)
        missing_refs = self._cross_reference(inline_citations, references)
        format_issues = self._validate_format(text, citation_style, inline_citations, references)

        return {
            "citations_found": len(inline_citations),
            "citation_style": citation_style,
            "inline_citations": inline_citations,
            "references": references,
            "reference_count": len(references),
            "missing_references": missing_refs,
            "format_issues": format_issues,
        }

    # ------------------------------------------------------------------
    def _extract_inline_citations(self, text: str) -> List[Dict[str, Any]]:
        """Extract all inline citations from text."""
        citations: List[Dict[str, Any]] = []
        seen: Set[str] = set()

        # APA-style: (Author, Year)
        for match in _APA_INLINE.finditer(text):
            key = f"apa:{match.group(1)}:{match.group(2)}"
            if key not in seen:
                seen.add(key)
                citations.append(
                    {
                        "style": "APA",
                        "text": match.group(0),
                        "author": match.group(1),
                        "year": match.group(2),
                        "position": {"start": match.start(), "end": match.end()},
                    }
                )

        # MLA-style: (Author Page)
        for match in _MLA_INLINE.finditer(text):
            key = f"mla:{match.group(1)}:{match.group(2)}"
            # Avoid double-counting with APA (APA has comma before year)
            full = match.group(0)
            if key not in seen and "," not in full:
                seen.add(key)
                citations.append(
                    {
                        "style": "MLA",
                        "text": match.group(0),
                        "author": match.group(1),
                        "page": match.group(2),
                        "position": {"start": match.start(), "end": match.end()},
                    }
                )

        # IEEE-style: [1], [2-5]
        for match in _IEEE_INLINE.finditer(text):
            key = f"ieee:{match.group(1)}"
            if key not in seen:
                seen.add(key)
                numbers_str = match.group(1)
                citations.append(
                    {
                        "style": "IEEE",
                        "text": match.group(0),
                        "numbers": numbers_str,
                        "position": {"start": match.start(), "end": match.end()},
                    }
                )

        # Harvard-style: (Author Year) — no comma
        for match in _HARVARD_INLINE.finditer(text):
            key = f"harvard:{match.group(1)}:{match.group(2)}"
            if key not in seen:
                seen.add(key)
                citations.append(
                    {
                        "style": "Harvard",
                        "text": match.group(0),
                        "author": match.group(1),
                        "year": match.group(2),
                        "position": {"start": match.start(), "end": match.end()},
                    }
                )

        return citations

    # ------------------------------------------------------------------
    def _detect_citation_style(self, text: str, inline_citations: List[Dict[str, Any]]) -> str:
        """Determine the dominant citation style in the text."""
        style_counts: Dict[str, int] = {}
        for cit in inline_citations:
            style = cit.get("style", "unknown")
            style_counts[style] = style_counts.get(style, 0) + 1

        if not style_counts:
            # Check for Chicago-style footnote markers
            chicago_matches = _CHICAGO_INLINE.findall(text)
            if len(chicago_matches) >= 2:
                return "Chicago"
            return "unknown"

        return max(style_counts, key=style_counts.get)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    def _extract_references(self, text: str) -> List[Dict[str, Any]]:
        """Extract reference list entries from the end of the text."""
        references: List[Dict[str, Any]] = []

        # Try to find a references section
        ref_section = self._find_reference_section(text)
        if not ref_section:
            ref_section = text  # search entire text as fallback

        # Numbered references [1] ...
        for match in _IEEE_REFERENCE.finditer(ref_section):
            references.append(
                {
                    "number": int(match.group(1)),
                    "text": match.group(2).strip(),
                    "style": "IEEE",
                }
            )

        # APA-style references: Author, A. B. (Year). Title.
        if not references:
            for match in _APA_REFERENCE.finditer(ref_section):
                references.append(
                    {
                        "author": match.group(1).strip(),
                        "year": match.group(2),
                        "title": match.group(3).strip(),
                        "style": "APA",
                    }
                )

        # Fallback: author-year pattern
        if not references:
            for match in _AUTHOR_YEAR_REFERENCE.finditer(ref_section):
                references.append(
                    {
                        "author": match.group(1).strip().rstrip(",. "),
                        "year": match.group(2),
                        "style": "generic",
                    }
                )

        return references

    # ------------------------------------------------------------------
    @staticmethod
    def _find_reference_section(text: str) -> Optional[str]:
        """Locate the references/bibliography section of the text."""
        patterns = [
            r"(?i)\n\s*(?:references|bibliography|works\s+cited|sources)\s*\n",
            r"(?i)\n\s*(?:references|bibliography|works\s+cited|sources)\s*$",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return text[match.start() :]
        return None

    # ------------------------------------------------------------------
    def _cross_reference(
        self,
        inline_citations: List[Dict[str, Any]],
        references: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Check which inline citations lack a corresponding reference entry."""
        missing = []
        if not inline_citations or not references:
            return missing

        # Build lookup sets from references
        ref_authors = set()
        ref_numbers = set()
        for ref in references:
            if "author" in ref:
                # Normalize: take last name
                author_parts = ref["author"].split(",")
                if author_parts:
                    ref_authors.add(author_parts[0].strip().lower())
            if "number" in ref:
                ref_numbers.add(ref["number"])

        for cit in inline_citations:
            found = False
            if cit["style"] == "IEEE":
                # Parse numbers
                nums_str = cit.get("numbers", "")
                nums = re.findall(r"\d+", nums_str)
                for n in nums:
                    if int(n) in ref_numbers:
                        found = True
                        break
                if not found and nums:
                    missing.append(
                        {
                            "citation": cit["text"],
                            "reason": f"No reference entry found for number(s) {nums_str}",
                        }
                    )
            elif "author" in cit:
                author_lower = cit["author"].split()[0].lower() if cit["author"] else ""
                if author_lower in ref_authors:
                    found = True
                if not found and author_lower:
                    missing.append(
                        {
                            "citation": cit["text"],
                            "reason": f"No reference entry found for author '{cit['author']}'",
                        }
                    )

        return missing

    # ------------------------------------------------------------------
    def _validate_format(
        self,
        text: str,
        style: str,
        inline_citations: List[Dict[str, Any]],
        references: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Check for citation format consistency issues."""
        issues = []

        # Check mixed styles
        styles_used = set(c.get("style") for c in inline_citations)
        if len(styles_used) > 1:
            issues.append(
                {
                    "type": "mixed_styles",
                    "message": f"Multiple citation styles detected: {', '.join(sorted(styles_used))}. Use a single consistent style.",
                    "severity": "warning",
                }
            )

        # Check for inline citations without references section
        if inline_citations and not references:
            issues.append(
                {
                    "type": "missing_references_section",
                    "message": "Inline citations found but no reference list/bibliography detected.",
                    "severity": "critical",
                }
            )

        # Check numbering gaps for IEEE
        if style == "IEEE" and references:
            ref_nums = sorted(r.get("number", 0) for r in references if "number" in r)
            if ref_nums:
                expected = list(range(1, ref_nums[-1] + 1))
                missing_nums = set(expected) - set(ref_nums)
                if missing_nums:
                    issues.append(
                        {
                            "type": "numbering_gap",
                            "message": f"Gap in reference numbering. Missing: {sorted(missing_nums)}",
                            "severity": "warning",
                        }
                    )

        # Check for references not cited
        if references and inline_citations:
            cited_numbers = set()
            cited_authors = set()
            for cit in inline_citations:
                if "numbers" in cit:
                    for n in re.findall(r"\d+", cit["numbers"]):
                        cited_numbers.add(int(n))
                if "author" in cit:
                    cited_authors.add(cit["author"].split()[0].lower())

            for ref in references:
                ref_cited = False
                if "number" in ref and ref["number"] in cited_numbers:
                    ref_cited = True
                if "author" in ref:
                    author_lower = ref["author"].split(",")[0].strip().lower()
                    if author_lower in cited_authors:
                        ref_cited = True
                if not ref_cited:
                    ref_label = ref.get("text", ref.get("author", "unknown"))[:60]
                    issues.append(
                        {
                            "type": "uncited_reference",
                            "message": f"Reference appears to be uncited: '{ref_label}...'",
                            "severity": "info",
                        }
                    )

        return issues
