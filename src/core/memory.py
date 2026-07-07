"""Per-user short-term conversation memory (Redis-backed, in-process fallback).

Stores the last N (user, assistant) turns so chat replies have context. This is
deliberately short-term — enough for a coherent conversation, not a long-term
knowledge store. Keys expire after a day of inactivity.
"""
from __future__ import annotations

import json

from src.config import get_settings
from src.core import store

_TTL_HINT = 86_400  # not enforced on lists in fallback; Redis lists persist here


def _key(user_id: int) -> str:
    return f"mem:{user_id}"


async def remember(user_id: int, user_msg: str, assistant_msg: str) -> None:
    """Append one exchange to the user's rolling memory."""
    turns = get_settings().memory_turns
    payload = json.dumps({"u": user_msg[:1000], "a": assistant_msg[:1000]})
    await store.push_trim(_key(user_id), payload, maxlen=turns)


async def recent(user_id: int) -> list[dict]:
    """Return recent turns oldest→newest (chronological), for prompt context."""
    turns = get_settings().memory_turns
    raw = await store.lrange(_key(user_id), turns)
    out: list[dict] = []
    for item in reversed(raw):  # stored newest-first; flip to chronological
        try:
            out.append(json.loads(item))
        except (json.JSONDecodeError, TypeError):
            continue
    return out


async def as_context(user_id: int) -> str:
    """Render recent turns as a compact text block for the system prompt."""
    turns = await recent(user_id)
    if not turns:
        return ""
    lines = [f"User: {t['u']}\nAssistant: {t['a']}" for t in turns if "u" in t and "a" in t]
    return "Recent conversation:\n" + "\n".join(lines)
