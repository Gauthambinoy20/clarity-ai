"""
Ollama-based humanizer -- rewrites text through a local LLM with
style-specific prompting to produce human-sounding output.
"""

import logging
from typing import Dict

import httpx

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"

# ---------------------------------------------------------------------------
# Style-specific system prompts
# ---------------------------------------------------------------------------
STYLE_PROMPTS: Dict[str, str] = {
    "academic": (
        "You are a skilled academic writer rewriting the following text. "
        "Your STRICT rules:\n"
        "1. Preserve the original meaning, facts, and arguments exactly.\n"
        "2. Vary sentence length naturally -- mix short punchy sentences with "
        "longer, more detailed ones.\n"
        "3. Use contractions sparingly (only where natural in academic writing).\n"
        "4. NEVER use these AI buzzwords: leverage, utilize, delve, multifaceted, "
        "comprehensive, innovative, cutting-edge, groundbreaking, paramount, crucial.\n"
        "5. Write in a measured, scholarly tone with occasional first-person hedging "
        "(e.g., 'it appears that', 'the evidence suggests').\n"
        "6. Use field-appropriate terminology but avoid unnecessary jargon.\n"
        "7. Make paragraph transitions feel organic, not formulaic.\n"
        "8. Do NOT add new information or opinions not present in the original.\n"
        "9. Output ONLY the rewritten text, nothing else."
    ),
    "casual": (
        "You are a friendly, natural writer rewriting the following text in a "
        "conversational tone. Your STRICT rules:\n"
        "1. Preserve the original meaning and key points exactly.\n"
        "2. Use contractions freely (don't, won't, it's, etc.).\n"
        "3. Vary sentence length a lot -- some very short, some longer.\n"
        "4. NEVER use these AI buzzwords: leverage, utilize, delve, multifaceted, "
        "comprehensive, innovative, cutting-edge, groundbreaking, paramount, crucial.\n"
        "5. Write like you're explaining to a smart friend over coffee.\n"
        "6. Occasionally start sentences with 'And', 'But', 'So'.\n"
        "7. Use simple, everyday words instead of fancy ones.\n"
        "8. It's okay to add brief parenthetical asides or rhetorical questions.\n"
        "9. Do NOT add new facts or change the meaning.\n"
        "10. Output ONLY the rewritten text, nothing else."
    ),
    "professional": (
        "You are a polished business writer rewriting the following text. "
        "Your STRICT rules:\n"
        "1. Preserve all original meaning, data, and conclusions exactly.\n"
        "2. Use contractions where natural in professional communication "
        "(e.g., 'it's clear that' is fine).\n"
        "3. Vary sentence structure -- mix simple direct statements with "
        "compound sentences.\n"
        "4. NEVER use these AI buzzwords: leverage, utilize, delve, multifaceted, "
        "comprehensive, innovative, cutting-edge, groundbreaking, paramount, crucial, "
        "synergy, paradigm, holistic.\n"
        "5. Be clear and direct. Avoid waffling.\n"
        "6. Use active voice whenever possible.\n"
        "7. Keep a confident but not arrogant tone.\n"
        "8. Do NOT add new information or change the meaning.\n"
        "9. Output ONLY the rewritten text, nothing else."
    ),
    "creative": (
        "You are a talented creative writer rewriting the following text with flair. "
        "Your STRICT rules:\n"
        "1. Preserve the core meaning and all facts exactly.\n"
        "2. Use contractions naturally and freely.\n"
        "3. Vary sentence length dramatically -- fragments are welcome, "
        "and so are flowing longer sentences.\n"
        "4. NEVER use these AI buzzwords: leverage, utilize, delve, multifaceted, "
        "comprehensive, innovative, cutting-edge, groundbreaking, paramount, crucial.\n"
        "5. Use vivid, concrete language. Show, don't tell.\n"
        "6. Add subtle rhythm and personality to the prose.\n"
        "7. Occasional metaphors or analogies are welcome if they fit.\n"
        "8. Use interesting sentence openers -- avoid starting every sentence "
        "the same way.\n"
        "9. Do NOT add new facts or substantially alter the meaning.\n"
        "10. Output ONLY the rewritten text, nothing else."
    ),
}


class OllamaHumanizer:
    """
    Rewrites text using a locally-running Ollama LLM instance with
    style-specific prompting.
    """

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        timeout: int = 120,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------
    async def humanize(
        self,
        text: str,
        style: str = "academic",
        model: str = "mistral:7b-instruct",
        temperature: float = 0.85,
    ) -> str:
        """
        Rewrite *text* via Ollama.

        Falls back to returning the original text with a warning note if
        Ollama is unreachable or returns an error.
        """
        if not text or not text.strip():
            return text

        system_prompt = STYLE_PROMPTS.get(style, STYLE_PROMPTS["academic"])

        payload = {
            "model": model,
            "prompt": text,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": 0.92,
                "repeat_penalty": 1.15,
                "num_predict": max(len(text.split()) * 3, 512),
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                rewritten = data.get("response", "").strip()

                if not rewritten:
                    logger.warning("Ollama returned empty response; using original text.")
                    return text

                return rewritten

        except httpx.ConnectError:
            logger.warning(
                "Could not connect to Ollama at %s. Returning original text.",
                self.base_url,
            )
            return text + "\n\n[Note: Ollama LLM rewriting was unavailable. Text is unchanged.]"
        except httpx.TimeoutException:
            logger.warning("Ollama request timed out after %ds.", self.timeout)
            return text + "\n\n[Note: Ollama LLM rewriting timed out. Text is unchanged.]"
        except httpx.HTTPStatusError as exc:
            logger.warning("Ollama HTTP error %s: %s", exc.response.status_code, exc)
            return text + "\n\n[Note: Ollama returned an error. Text is unchanged.]"
        except Exception as exc:
            logger.exception("Unexpected error calling Ollama: %s", exc)
            return text + "\n\n[Note: Ollama LLM rewriting failed. Text is unchanged.]"

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------
    async def is_available(self) -> bool:
        """Return True if Ollama is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False
