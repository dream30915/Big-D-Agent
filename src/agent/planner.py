"""Planner — turns a complex request into a short, ordered plan.

Used by the coordinator only for tasks that look complex, so we don't spend
tokens planning trivial messages. Degrades gracefully: if the LLM is
unavailable, planning simply returns None and the coordinator proceeds without
a plan (never blocks a reply).
"""
from __future__ import annotations

from src.agent.router import model_for
from src.agent.intent import Intent
from src.llm.openrouter import LLMError, llm_client

_SYSTEM = (
    "You are a planning assistant. Output a short numbered plan (3-6 steps), "
    "nothing else. Match the user's language (Thai or English)."
)


async def make_plan(text: str) -> str | None:
    """Return a brief numbered plan, or None if planning isn't possible."""
    try:
        result = await llm_client.complete(
            f"Break this task into a few concise, ordered steps:\n\n{text}",
            model=model_for(Intent.ANALYZE),  # quality tier for planning
            system=_SYSTEM,
            temperature=0.3,
            max_tokens=350,
        )
        return result.text
    except LLMError:
        return None
