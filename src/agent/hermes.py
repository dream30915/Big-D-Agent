"""Hermes — the decision engine.

Flow for every incoming message:
  1. Ethics gate (refuse blocked categories).
  2. Classify intent (cheap keyword pass).
  3. Route to a skill if the intent maps to one; otherwise answer with the LLM
     on the intent-appropriate model tier.
  4. For scraping/browsing, feed the fetched text back through the LLM so the
     user gets a summary, not a raw dump.

This is deliberately small and legible — it is the seam every advanced feature
(multi-agent, self-optimization) will extend later.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.agent.intent import Intent, classify
from src.agent.router import model_for
from src.config import get_settings
from src.core import ethics
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


async def handle_message(text: str) -> AgentReply:
    settings = get_settings()

    if settings.enable_ethics_module:
        verdict = ethics.check(text)
        if not verdict.allowed:
            logger.info("ethics blocked message (category={})", verdict.category)
            return AgentReply(
                text="ขอโทษครับ ผมไม่สามารถช่วยเรื่องนี้ได้ / I can't help with that request.",
                intent=Intent.CHAT,
            )

    intent = classify(text)
    logger.debug("intent={} for message len={}", intent, len(text))

    skill_name = _INTENT_SKILL.get(intent)
    if skill_name and skill_name in SKILLS:
        result = await SKILLS[skill_name].run(text)
        if not result.ok:
            return AgentReply(text=result.text, intent=intent, skill=skill_name)
        # For fetched content, summarise; content/support/analysis skills already
        # return finished text.
        if intent in (Intent.SCRAPE, Intent.BROWSE):
            summary = await _summarise(result.text, source=result.meta or {})
            return AgentReply(text=summary, intent=intent, skill=skill_name)
        return AgentReply(text=result.text, intent=intent, skill=skill_name)

    # Plain chat.
    try:
        reply = await llm_client.complete(
            text, model=model_for(intent), system=_CHAT_SYSTEM
        )
        return AgentReply(text=reply.text, intent=intent)
    except LLMError as exc:
        logger.error("chat completion failed: {}", exc)
        return AgentReply(
            text="ตอนนี้ AI ยังไม่พร้อม (ตรวจ OPENROUTER_API_KEY). / AI is unavailable — check OPENROUTER_API_KEY.",
            intent=intent,
        )


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
