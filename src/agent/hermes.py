"""Hermes — the decision engine.

Flow for every incoming message:
  1. Rate limit + daily budget guard (cheap, before any token spend).
  2. Ethics gate (refuse blocked categories).
  3. Classify intent (cheap keyword pass).
  4. Route to a skill if the intent maps to one; otherwise answer with the LLM
     on the intent-appropriate model tier, using the user's short-term memory.
  5. For scraping/browsing, feed the fetched text back through the LLM so the
     user gets a summary, not a raw dump.

This is deliberately small and legible — it is the seam every advanced feature
(multi-agent, self-optimization) will extend later.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.agent.intent import Intent, classify
from src.agent.router import model_for
from src.config import get_settings
from src.core import costguard, ethics, memory
from src.core.logging import logger
from src.llm.openrouter import LLMError, llm_client
from src.skills import SKILLS

# Which intents are served by a named skill vs. a plain LLM answer.
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


@dataclass
class AgentReply:
    text: str
    intent: Intent
    skill: str | None = None
    blocked: str | None = None  # set when a guard refused the request


async def handle_message(text: str, user_id: int | None = None) -> AgentReply:
    settings = get_settings()

    # 1. Guards — cheap checks before any work / token spend.
    if user_id is not None:
        rate = await costguard.check_rate(user_id)
        if not rate.allowed:
            return AgentReply(
                text="⏳ ช้าลงหน่อยนะครับ ส่งบ่อยเกินไป / Too many requests — please slow down.",
                intent=Intent.CHAT,
                blocked="rate_limited",
            )
    budget = await costguard.check_budget()
    if not budget.allowed:
        logger.warning("request refused by budget guard: {}", budget.reason)
        return AgentReply(
            text="🛑 วันนี้ใช้งบ AI ครบแล้ว เดี๋ยวพรุ่งนี้รีเซ็ต / Daily AI budget reached — resets tomorrow.",
            intent=Intent.CHAT,
            blocked=budget.reason,
        )

    # 2. Ethics.
    if settings.enable_ethics_module:
        verdict = ethics.check(text)
        if not verdict.allowed:
            logger.info("ethics blocked message (category={})", verdict.category)
            return AgentReply(
                text="ขอโทษครับ ผมไม่สามารถช่วยเรื่องนี้ได้ / I can't help with that request.",
                intent=Intent.CHAT,
                blocked="ethics",
            )

    # 3. Intent.
    intent = classify(text)
    logger.debug("intent={} for message len={}", intent, len(text))

    # 4. Skill path.
    skill_name = _INTENT_SKILL.get(intent)
    if skill_name and skill_name in SKILLS:
        result = await SKILLS[skill_name].run(text)
        if not result.ok:
            return AgentReply(text=result.text, intent=intent, skill=skill_name)
        if intent in (Intent.SCRAPE, Intent.BROWSE):
            summary = await _summarise(result.text, source=result.meta or {})
            return AgentReply(text=summary, intent=intent, skill=skill_name)
        return AgentReply(text=result.text, intent=intent, skill=skill_name)

    # 5. Plain chat — with short-term memory for continuity.
    system = _CHAT_SYSTEM
    if user_id is not None:
        context = await memory.as_context(user_id)
        if context:
            system = f"{_CHAT_SYSTEM}\n\n{context}"
    try:
        reply = await llm_client.complete(text, model=model_for(intent), system=system)
    except LLMError as exc:
        logger.error("chat completion failed: {}", exc)
        return AgentReply(
            text="ตอนนี้ AI ยังไม่พร้อม (ตรวจ OPENROUTER_API_KEY). / AI is unavailable — check OPENROUTER_API_KEY.",
            intent=intent,
        )

    if user_id is not None:
        await memory.remember(user_id, text, reply.text)
    return AgentReply(text=reply.text, intent=intent)


async def _summarise(content: str, *, source: dict) -> str:
    title = source.get("title") or source.get("url", "the page")
    try:
        result = await llm_client.complete(
            f"Summarise the following page content in a few clear bullet points:\n\n{content}",
            system="You summarise web content faithfully. Do not invent facts.",
        )
        return f"📄 {title}\n\n{result.text}"
    except LLMError:
        # No LLM? Still return something useful.
        return f"📄 {title}\n\n{content[:800]}"
