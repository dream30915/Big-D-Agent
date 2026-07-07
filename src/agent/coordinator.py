"""Coordinator — the multi-agent brain.

Orchestrates: (router = intent) → optional (planner) → (specialist executor).
Enabled by the ENABLE_MULTI_AGENT flag; when off, Hermes uses the direct
single-specialist path instead. The coordinator adds a planning step for
complex requests so the user sees the approach, then executes with the same
specialist layer the direct path uses (no duplicated logic, same cost guard).
"""
from __future__ import annotations

from dataclasses import dataclass

from src.agent import planner
from src.agent.intent import Intent
from src.agent.specialists import SPECIALIST_NAME, run_intent
from src.core.logging import logger

# Signals that a request is worth planning (multi-step / longer work).
_COMPLEX_HINTS = (
    "then", "after that", "step", "steps", "first", "finally", "plan",
    "และ", "จากนั้น", "ขั้นตอน", "แผน", "หลังจาก",
)


@dataclass
class CoordResult:
    text: str
    specialist: str
    planned: bool


def _is_complex(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) > 160:
        return True
    lowered = stripped.lower()
    if any(h in lowered for h in _COMPLEX_HINTS):
        return True
    # More than one sentence/question also reads as multi-part.
    return (stripped.count(".") + stripped.count("?") + stripped.count("\n")) >= 2


async def run(text: str, intent: Intent) -> CoordResult:
    plan: str | None = None
    if _is_complex(text):
        plan = await planner.make_plan(text)
        if plan:
            logger.info("coordinator planned a complex task ({} chars)", len(text))

    body, skill = await run_intent(text, intent)
    specialist = skill or SPECIALIST_NAME.get(intent, "GeneralSpecialist")

    if plan:
        out = f"🗺️ *แผนงาน / Plan*\n{plan}\n\n———\n{body}"
    else:
        out = body
    return CoordResult(text=out, specialist=specialist, planned=plan is not None)
