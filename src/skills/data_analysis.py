"""Data analysis skill — reason over finance/business questions on the quality tier."""
from __future__ import annotations

from src.config import get_settings
from src.llm.openrouter import LLMError, llm_client
from src.skills.base import Skill, SkillResult

_SYSTEM = (
    "You are a rigorous business/data analyst. Show the reasoning and any "
    "assumptions. If numbers are missing, state what you'd need rather than "
    "guessing. Never fabricate figures."
)


async def _handle(text: str) -> SkillResult:
    settings = get_settings()
    try:
        result = await llm_client.complete(
            text, model=settings.openrouter_model_quality, system=_SYSTEM, temperature=0.3
        )
    except LLMError as exc:
        return SkillResult(ok=False, text=f"Analysis failed: {exc}")
    return SkillResult(ok=True, text=result.text, meta={"model": result.model})


data_analysis = Skill(
    name="data_analysis",
    description="Analyse finance/business questions without fabricating numbers.",
    handler=_handle,
)
