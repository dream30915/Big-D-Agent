"""Specialists — the layer that actually does the work for a given intent.

A specialist is either backed by an existing skill (content/support/analysis/
scrape/browse) or by a tailored LLM call (coding/general). Everything goes
through `llm_client`, so the cost guard, usage tracking, and fallback apply
uniformly. `run_intent` is the single executor shared by the direct path
(Hermes) and the multi-agent coordinator — no duplicated dispatch logic.
"""
from __future__ import annotations

from src.agent.intent import Intent
from src.agent.router import model_for
from src.agent.summarize import summarise_page
from src.llm.openrouter import LLMError, llm_client
from src.skills import SKILLS

# Human-readable specialist names, for display in the coordinator's output.
SPECIALIST_NAME: dict[Intent, str] = {
    Intent.SCRAPE: "ResearchSpecialist",
    Intent.BROWSE: "ResearchSpecialist",
    Intent.CONTENT: "ContentSpecialist",
    Intent.SUPPORT: "SupportSpecialist",
    Intent.ANALYZE: "AnalysisSpecialist",
    Intent.CODE: "CodingSpecialist",
    Intent.CHAT: "GeneralSpecialist",
}

# Intents handled by a named skill.
_INTENT_SKILL: dict[Intent, str] = {
    Intent.SCRAPE: "web_scraping",
    Intent.BROWSE: "browser_automation",
    Intent.CONTENT: "content_creation",
    Intent.SUPPORT: "customer_service",
    Intent.ANALYZE: "data_analysis",
}

_CHAT_SYSTEM = (
    "You are Big-D-Agent, a capable assistant on Telegram. Be concise and "
    "helpful. Reply in the user's language (Thai or English)."
)
_CODING_SYSTEM = (
    "You are a senior software engineer. Give correct, runnable code with a "
    "short explanation. Prefer standard libraries. State assumptions instead of "
    "guessing. Reply in the user's language (Thai or English)."
)
_AI_UNAVAILABLE = (
    "ตอนนี้ AI ยังไม่พร้อม (ตรวจ OPENROUTER_API_KEY). / AI is unavailable — check OPENROUTER_API_KEY."
)


async def run_intent(text: str, intent: Intent, *, system_extra: str = "") -> tuple[str, str | None]:
    """Execute the specialist for an intent. Returns (reply_text, skill_name|None)."""
    skill_name = _INTENT_SKILL.get(intent)
    if skill_name and skill_name in SKILLS:
        result = await SKILLS[skill_name].run(text)
        if not result.ok:
            return result.text, skill_name
        if intent in (Intent.SCRAPE, Intent.BROWSE):
            return await summarise_page(result.text, result.meta or {}), skill_name
        return result.text, skill_name

    # LLM-backed specialists (coding / general chat).
    base = _CODING_SYSTEM if intent is Intent.CODE else _CHAT_SYSTEM
    system = f"{base}\n\n{system_extra}" if system_extra else base
    try:
        reply = await llm_client.complete(text, model=model_for(intent), system=system)
        return reply.text, None
    except LLMError:
        return _AI_UNAVAILABLE, None
