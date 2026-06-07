"""
Async source discovery -- searches multiple academic and web sources
in parallel to find potential origins for text passages.
"""

import asyncio
import logging
import math
import re
from collections import Counter
from typing import Any, Dict, List, Set, Tuple
from urllib.parse import quote_plus

import httpx

logger = logging.getLogger(__name__)

# Maximum number of sources to return per search engine
MAX_RESULTS_PER_ENGINE = 5
REQUEST_TIMEOUT = 15  # seconds


# ---------------------------------------------------------------------------
# Key-phrase extraction (lightweight TF-IDF-style)
# ---------------------------------------------------------------------------

# Common English stop words
_STOP_WORDS: Set[str] = {
    "a",
    "about",
    "above",
    "after",
    "again",
    "against",
    "all",
    "am",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "below",
    "between",
    "both",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "doing",
    "down",
    "during",
    "each",
    "few",
    "for",
    "from",
    "further",
    "get",
    "got",
    "had",
    "has",
    "have",
    "having",
    "he",
    "her",
    "here",
    "hers",
    "herself",
    "him",
    "himself",
    "his",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "itself",
    "just",
    "me",
    "might",
    "more",
    "most",
    "my",
    "myself",
    "no",
    "nor",
    "not",
    "now",
    "of",
    "off",
    "on",
    "once",
    "only",
    "or",
    "other",
    "our",
    "ours",
    "ourselves",
    "out",
    "over",
    "own",
    "same",
    "she",
    "should",
    "so",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "theirs",
    "them",
    "themselves",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "to",
    "too",
    "under",
    "until",
    "up",
    "us",
    "very",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "whom",
    "why",
    "will",
    "with",
    "would",
    "you",
    "your",
    "yours",
    "yourself",
    "yourselves",
}


def extract_key_phrases(
    text: str, top_n: int = 5, ngram_range: Tuple[int, int] = (2, 4)
) -> List[str]:
    """
    Extract the most informative n-gram phrases from *text* using a
    simple TF-IDF-like scoring (term frequency penalised by commonness).

    Returns up to *top_n* phrases sorted by score descending.
    """
    words = re.sub(r"[^\w\s]", "", text.lower()).split()
    words = [w for w in words if w not in _STOP_WORDS and len(w) > 2]

    if not words:
        return []

    # Build n-gram candidates
    ngram_counts: Counter = Counter()
    for n in range(ngram_range[0], ngram_range[1] + 1):
        for i in range(len(words) - n + 1):
            gram = " ".join(words[i : i + n])
            ngram_counts[gram] += 1

    # Score: frequency * average word length (proxy for specificity)
    scored: List[Tuple[str, float]] = []
    for gram, count in ngram_counts.items():
        avg_word_len = sum(len(w) for w in gram.split()) / len(gram.split())
        score = count * math.log1p(avg_word_len)
        scored.append((gram, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [phrase for phrase, _ in scored[:top_n]]


# ---------------------------------------------------------------------------
# Source search engines (all async)
# ---------------------------------------------------------------------------


async def _search_duckduckgo(query: str, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Search DuckDuckGo instant-answer API."""
    results: List[Dict[str, Any]] = []
    try:
        url = "https://api.duckduckgo.com/"
        params = {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"}
        resp = await client.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        # Abstract result
        if data.get("Abstract"):
            results.append(
                {
                    "title": data.get("Heading", ""),
                    "url": data.get("AbstractURL", ""),
                    "snippet": data.get("Abstract", "")[:500],
                    "source_engine": "duckduckgo",
                }
            )

        # Related topics
        for topic in (data.get("RelatedTopics") or [])[:MAX_RESULTS_PER_ENGINE]:
            if isinstance(topic, dict) and topic.get("FirstURL"):
                results.append(
                    {
                        "title": topic.get("Text", "")[:200],
                        "url": topic["FirstURL"],
                        "snippet": topic.get("Text", "")[:500],
                        "source_engine": "duckduckgo",
                    }
                )
    except Exception as exc:
        logger.debug("DuckDuckGo search failed: %s", exc)
    return results[:MAX_RESULTS_PER_ENGINE]


async def _search_semantic_scholar(query: str, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Search Semantic Scholar API for academic papers."""
    results: List[Dict[str, Any]] = []
    try:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": MAX_RESULTS_PER_ENGINE,
            "fields": "title,abstract,url,year,authors",
        }
        resp = await client.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        for paper in data.get("data") or []:
            authors = ", ".join(a.get("name", "") for a in (paper.get("authors") or [])[:3])
            results.append(
                {
                    "title": paper.get("title", ""),
                    "url": paper.get(
                        "url", f"https://www.semanticscholar.org/paper/{paper.get('paperId', '')}"
                    ),
                    "snippet": (paper.get("abstract") or "")[:500],
                    "source_engine": "semantic_scholar",
                    "year": paper.get("year"),
                    "authors": authors,
                }
            )
    except Exception as exc:
        logger.debug("Semantic Scholar search failed: %s", exc)
    return results[:MAX_RESULTS_PER_ENGINE]


async def _search_crossref(query: str, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Search CrossRef API for DOI / publication metadata."""
    results: List[Dict[str, Any]] = []
    try:
        url = "https://api.crossref.org/works"
        params = {
            "query": query,
            "rows": MAX_RESULTS_PER_ENGINE,
            "select": "DOI,title,abstract,URL,author,published-print",
        }
        headers = {"User-Agent": "ClarityAI/1.0 (mailto:admin@clarityai.local)"}
        resp = await client.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("message", {}).get("items") or []:
            title = (item.get("title") or [""])[0]
            authors = ", ".join(
                f"{a.get('given', '')} {a.get('family', '')}"
                for a in (item.get("author") or [])[:3]
            )
            abstract = (item.get("abstract") or "")[:500]
            # Strip HTML tags from abstract
            abstract = re.sub(r"<[^>]+>", "", abstract)
            results.append(
                {
                    "title": title,
                    "url": item.get("URL", ""),
                    "snippet": abstract,
                    "source_engine": "crossref",
                    "doi": item.get("DOI", ""),
                    "authors": authors,
                }
            )
    except Exception as exc:
        logger.debug("CrossRef search failed: %s", exc)
    return results[:MAX_RESULTS_PER_ENGINE]


async def _search_openalex(query: str, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Search OpenAlex API for scholarly works."""
    results: List[Dict[str, Any]] = []
    try:
        url = "https://api.openalex.org/works"
        params = {
            "search": query,
            "per_page": MAX_RESULTS_PER_ENGINE,
            "select": "id,title,doi,publication_year,authorships,abstract_inverted_index",
        }
        headers = {"User-Agent": "ClarityAI/1.0 (mailto:admin@clarityai.local)"}
        resp = await client.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        for work in data.get("results") or []:
            # Reconstruct abstract from inverted index
            abstract = ""
            inv_index = work.get("abstract_inverted_index")
            if inv_index and isinstance(inv_index, dict):
                positions: List[Tuple[int, str]] = []
                for word, idxs in inv_index.items():
                    for idx in idxs:
                        positions.append((idx, word))
                positions.sort()
                abstract = " ".join(w for _, w in positions)[:500]

            authors = ", ".join(
                (a.get("author", {}).get("display_name", ""))
                for a in (work.get("authorships") or [])[:3]
            )
            doi = work.get("doi") or ""
            work_url = doi if doi.startswith("http") else work.get("id", "")

            results.append(
                {
                    "title": work.get("title", ""),
                    "url": work_url,
                    "snippet": abstract,
                    "source_engine": "openalex",
                    "year": work.get("publication_year"),
                    "authors": authors,
                }
            )
    except Exception as exc:
        logger.debug("OpenAlex search failed: %s", exc)
    return results[:MAX_RESULTS_PER_ENGINE]


async def _search_wikipedia(query: str, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Search Wikipedia API."""
    results: List[Dict[str, Any]] = []
    try:
        url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": MAX_RESULTS_PER_ENGINE,
            "format": "json",
            "srprop": "snippet|titlesnippet",
        }
        resp = await client.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("query", {}).get("search") or []:
            title = item.get("title", "")
            snippet = re.sub(r"<[^>]+>", "", item.get("snippet", ""))
            page_url = f"https://en.wikipedia.org/wiki/{quote_plus(title.replace(' ', '_'))}"
            results.append(
                {
                    "title": title,
                    "url": page_url,
                    "snippet": snippet[:500],
                    "source_engine": "wikipedia",
                }
            )
    except Exception as exc:
        logger.debug("Wikipedia search failed: %s", exc)
    return results[:MAX_RESULTS_PER_ENGINE]


async def _search_arxiv(query: str, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Search arXiv API."""
    results: List[Dict[str, Any]] = []
    try:
        url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{quote_plus(query)}",
            "start": 0,
            "max_results": MAX_RESULTS_PER_ENGINE,
        }
        resp = await client.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()

        # Parse Atom XML
        import xml.etree.ElementTree as ET

        root = ET.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        for entry in root.findall("atom:entry", ns):
            title_el = entry.find("atom:title", ns)
            summary_el = entry.find("atom:summary", ns)
            link_el = entry.find("atom:id", ns)
            authors_els = entry.findall("atom:author/atom:name", ns)

            title = (title_el.text or "").strip().replace("\n", " ") if title_el is not None else ""
            summary = (
                (summary_el.text or "").strip().replace("\n", " ")[:500]
                if summary_el is not None
                else ""
            )
            link = (link_el.text or "").strip() if link_el is not None else ""
            authors = ", ".join((a.text or "").strip() for a in (authors_els or [])[:3])

            results.append(
                {
                    "title": title,
                    "url": link,
                    "snippet": summary,
                    "source_engine": "arxiv",
                    "authors": authors,
                }
            )
    except Exception as exc:
        logger.debug("arXiv search failed: %s", exc)
    return results[:MAX_RESULTS_PER_ENGINE]


# ---------------------------------------------------------------------------
# Content extraction from URLs
# ---------------------------------------------------------------------------


async def fetch_page_content(url: str, client: httpx.AsyncClient, max_chars: int = 5000) -> str:
    """
    Fetch a URL and extract readable text via BeautifulSoup.
    Returns up to *max_chars* of text content.
    """
    try:
        resp = await client.get(
            url,
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "ClarityAI/1.0"},
        )
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "html" not in content_type and "text" not in content_type:
            return ""

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove scripts and styles
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception as exc:
        logger.debug("Failed to fetch %s: %s", url, exc)
        return ""


# ---------------------------------------------------------------------------
# Orchestrator: parallel search across all engines
# ---------------------------------------------------------------------------


class SourceDiscovery:
    """
    Discovers potential source material for a given text by querying
    multiple search APIs in parallel.
    """

    def __init__(self, top_phrases: int = 5) -> None:
        self.top_phrases = top_phrases

    async def search(self, text: str) -> Dict[str, Any]:
        """
        Extract key phrases from *text* and search all engines in parallel.

        Returns dict with ``key_phrases``, ``sources`` (list of source dicts),
        and ``engines_queried``.
        """
        phrases = extract_key_phrases(text, top_n=self.top_phrases)
        if not phrases:
            return {"key_phrases": [], "sources": [], "engines_queried": 0}

        query = " ".join(phrases[:3])  # use top 3 phrases as query

        async with httpx.AsyncClient() as client:
            tasks = [
                _search_duckduckgo(query, client),
                _search_semantic_scholar(query, client),
                _search_crossref(query, client),
                _search_openalex(query, client),
                _search_wikipedia(query, client),
                _search_arxiv(query, client),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

        all_sources: List[Dict[str, Any]] = []
        engines_succeeded = 0
        for result in results:
            if isinstance(result, list):
                all_sources.extend(result)
                if result:
                    engines_succeeded += 1
            elif isinstance(result, Exception):
                logger.debug("Search engine returned exception: %s", result)

        # Deduplicate by URL
        seen_urls: Set[str] = set()
        unique_sources: List[Dict[str, Any]] = []
        for src in all_sources:
            url = src.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_sources.append(src)

        return {
            "key_phrases": phrases,
            "sources": unique_sources,
            "engines_queried": 6,
            "engines_succeeded": engines_succeeded,
        }

    async def search_and_fetch(self, text: str, max_fetch: int = 10) -> Dict[str, Any]:
        """
        Search for sources AND fetch content from the top URLs.

        Returns the same dict as ``search()`` but with an added
        ``fetched_content`` key mapping URL -> extracted text.
        """
        search_result = await self.search(text)
        sources = search_result.get("sources", [])

        # Fetch content from top sources
        urls_to_fetch = [s["url"] for s in sources[:max_fetch] if s.get("url")]

        fetched: Dict[str, str] = {}
        if urls_to_fetch:
            async with httpx.AsyncClient() as client:
                tasks = [fetch_page_content(url, client) for url in urls_to_fetch]
                contents = await asyncio.gather(*tasks, return_exceptions=True)

            for url, content in zip(urls_to_fetch, contents):
                if isinstance(content, str) and content:
                    fetched[url] = content

        search_result["fetched_content"] = fetched
        return search_result
