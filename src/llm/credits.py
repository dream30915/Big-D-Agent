"""OpenRouter credit check — ported from the owner's Hermes credit_guard.py.

Returns remaining credit in USD, or None if it can't be read. Used by the
/credit admin command and surfaced on demand (kept off the hot path so /health
stays instant).
"""
from __future__ import annotations

import httpx

from src.config import get_settings
from src.core.logging import logger

_ENDPOINT = "https://openrouter.ai/api/v1/credits"


async def remaining_usd() -> float | None:
    settings = get_settings()
    if not settings.openrouter_configured:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                _ENDPOINT,
                headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
        return float(data.get("total_credits", 0)) - float(data.get("total_usage", 0))
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.debug("credit check failed: {}", exc)
        return None
