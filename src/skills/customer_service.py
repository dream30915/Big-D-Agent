"""Customer service skill — answer support-style questions on the fast tier."""
from __future__ import annotations

from src.config import get_settings
from src.llm.openrouter import LLMError, llm_client
from src.skills.base import Skill, SkillResult

_SYSTEM = (
    "You are a helpful, polite customer-support agent. Be clear and brief. If a "
    "request needs a human (refunds, account changes, payments), say so and "
    "offer to escalate rather than inventing an answer."
)


async def _handle(text: str) -> SkillResult:
    settings = get_settings()
    try:
        result = await llm_client.complete(
            text, model=settings.openrouter_model_fast, system=_SYSTEM, temperature=0.4
        )
    except LLMError as exc:
        return SkillResult(ok=False, text=f"Support reply failed: {exc}")
    return SkillResult(ok=True, text=result.text, meta={"model": result.model})


customer_service = Skill(
    name="customer_service",
    description="Answer FAQ / support questions; escalate what needs a human.",
    handler=_handle,
)
