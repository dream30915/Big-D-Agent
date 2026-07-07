"""Hermes — the decision engine.

Flow for every incoming message:
  1. Rate limit + daily budget guard (cheap, before any token spend).
  2. Ethics gate (refuse blocked categories).
  3. Classify intent (cheap keyword pass).
  4. Execute:
       * ENABLE_MULTI_AGENT on  → hand to the coordinator (router → planner →
         specialist).
       * off → run the single specialist directly (run_intent).
     Both reuse the same specialist layer, so cost guard / memory / fallback
     behave identically.

This is deliberately small and legible — the seam every advanced feature
extends.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.agent import coordinator
from src.agent.intent import Intent, classify
from src.agent.specialists import run_intent
from src.config import get_settings
from src.core import costguard, ethics, memory
from src.core.logging import logger


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
    logger.debug("intent={} multi_agent={}", intent, settings.enable_multi_agent)

    # Short-term memory context (chat continuity) for the LLM specialists.
    context = await memory.as_context(user_id) if user_id is not None else ""

    # 4. Execute.
    if settings.enable_multi_agent:
        result = await coordinator.run(text, intent)
        reply = AgentReply(text=result.text, intent=intent, skill=result.specialist)
    else:
        body, skill = await run_intent(text, intent, system_extra=context)
        reply = AgentReply(text=body, intent=intent, skill=skill)

    # Remember chat turns for continuity (skill replies are stateless).
    if user_id is not None and reply.skill in (None, "GeneralSpecialist", "CodingSpecialist"):
        await memory.remember(user_id, text, reply.text)
    return reply
