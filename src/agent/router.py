"""Model routing — map an intent to a cost/quality tier.

Cheap, well-bounded tasks (support replies, quick chat) use the fast tier.
Open-ended generation (content, analysis) uses the quality tier. Centralising
this keeps cost decisions in one auditable place.
"""
from __future__ import annotations

from src.agent.intent import Intent
from src.config import get_settings


def model_for(intent: Intent) -> str:
    """Return the OpenRouter model id for a given intent."""
    settings = get_settings()
    quality_intents = {Intent.CONTENT, Intent.ANALYZE, Intent.CODE}
    if intent in quality_intents:
        return settings.openrouter_model_quality
    return settings.openrouter_model_fast
