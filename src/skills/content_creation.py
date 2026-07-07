"""Content creation skill — generate marketing/social copy via the quality tier."""
from __future__ import annotations

from src.config import get_settings
from src.llm.openrouter import LLMError, llm_client
from src.skills.base import Skill, SkillResult

_SYSTEM = (
    "You are a concise, high-converting content writer. Produce ready-to-post "
    "copy. Match the language of the user's request (Thai or English)."
)


async def _handle(text: str) -> SkillResult:
    settings = get_settings()
    try:
        result = await llm_client.complete(
            text, model=settings.openrouter_model_quality, system=_SYSTEM, temperature=0.8
        )
    except LLMError as exc:
        return SkillResult(ok=False, text=f"Content generation failed: {exc}")
    return SkillResult(ok=True, text=result.text, meta={"model": result.model})


content_creation = Skill(
    name="content_creation",
    description="Generate marketing / social copy from a brief.",
    handler=_handle,
)
