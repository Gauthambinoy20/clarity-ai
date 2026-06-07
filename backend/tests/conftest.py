"""
Shared pytest fixtures for ClarityAI backend tests.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport


# ---------------------------------------------------------------------------
# Sample texts
# ---------------------------------------------------------------------------

# Clearly AI-written: heavy buzzword density, formal structure, AI-typical patterns
AI_TEXT = (
    "In today's modern landscape, it is important to note that artificial intelligence "
    "plays a crucial role in transforming how we utilize and leverage cutting-edge "
    "technologies. Holistic approaches to synergy enable multifaceted, comprehensive "
    "solutions that are robust and innovative. Furthermore, this essay will explore how "
    "groundbreaking paradigms can underscore pivotal changes across various key factors. "
    "To sum up, the seamless integration of these frameworks is paramount to achieving "
    "optimal outcomes and facilitating transformative progress in the ecosystem."
)

# Clearly human-written: conversational, personal, irregular structure
HUMAN_TEXT = (
    "So I finally got around to fixing that leak under the sink yesterday — took me way "
    "longer than expected because I couldn't find the right wrench. My neighbour ended up "
    "lending me one, which was great. Anyway, the whole thing cost me about thirty quid "
    "once I bought the new washer. Not bad really. I'd been putting it off for weeks "
    "because I was convinced it'd be some huge job, but turns out it was dead simple once "
    "I actually started. Funny how that goes."
)

# Borderline / mixed text
MIXED_TEXT = (
    "Research has shown that sleep plays an important role in memory consolidation. "
    "Studies from the past decade suggest people who sleep fewer than six hours a night "
    "perform worse on cognitive tasks. However, the relationship isn't simple — individual "
    "variation is enormous. Some folks genuinely thrive on less sleep, though they're rare. "
    "The practical takeaway: aim for seven to nine hours if you can manage it."
)

# Short text (too short for most detectors)
SHORT_TEXT = "Hello world."


# ---------------------------------------------------------------------------
# FastAPI test client fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    """Async test client for the ClarityAI FastAPI app.

    Uses an in-memory SQLite database so tests don't touch the real DB.
    """
    import os

    # Point to an in-memory DB for tests
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    from app.main import create_app
    from app.db.database import init_db

    app = create_app()
    await init_db()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
