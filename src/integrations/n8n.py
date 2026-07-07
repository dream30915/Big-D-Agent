"""n8n integration — fire an n8n workflow via its webhook.

Outbound only: the bot (or a scheduled task, or the API) POSTs a JSON payload to
a user-configured n8n webhook URL, optionally authenticated with N8N_API_KEY.
This is the "hands" of the system — it lets Big-D-Agent kick off visual
workflows for enterprise use. Everything degrades gracefully: if n8n isn't
configured or the call fails, we return a structured result, never raise.
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from src.config import get_settings
from src.core.logging import logger


@dataclass
class N8nResult:
    ok: bool
    status: int | None
    detail: str


def build_payload(
    text: str,
    *,
    user_id: int | None = None,
    chat_id: int | None = None,
    source: str = "bot",
    extra: dict | None = None,
) -> dict:
    """Assemble the JSON body sent to the n8n webhook."""
    payload: dict = {"source": source, "text": text}
    if user_id is not None:
        payload["user_id"] = user_id
    if chat_id is not None:
        payload["chat_id"] = chat_id
    if extra:
        payload.update(extra)
    return payload


async def trigger(payload: dict) -> N8nResult:
    """POST the payload to the configured n8n webhook."""
    settings = get_settings()
    if not settings.n8n_configured:
        return N8nResult(False, None, "n8n is not configured (set N8N_WEBHOOK_URL)")

    headers: dict[str, str] = {}
    if settings.n8n_api_key:
        # n8n accepts either a Bearer token or its X-N8N-Api-Key header depending
        # on how the webhook auth is set up; send both so either works.
        headers["Authorization"] = f"Bearer {settings.n8n_api_key}"
        headers["X-N8N-Api-Key"] = settings.n8n_api_key

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(settings.n8n_webhook_url, json=payload, headers=headers)
        ok = resp.status_code < 400
        detail = (resp.text or "")[:500]
        if not ok:
            logger.warning("n8n returned {}: {}", resp.status_code, detail)
        return N8nResult(ok=ok, status=resp.status_code, detail=detail)
    except httpx.HTTPError as exc:
        logger.warning("n8n trigger failed: {}", exc)
        return N8nResult(False, None, str(exc)[:200])
