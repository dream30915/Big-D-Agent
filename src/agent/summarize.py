"""Shared page summariser — used by both the direct path and the coordinator.

Kept in one place so scraping/browsing always summarise the same way (and so we
don't duplicate the "no LLM? still return something" fallback).
"""
from __future__ import annotations

from src.llm.openrouter import LLMError, llm_client


async def summarise_page(content: str, source: dict) -> str:
    title = source.get("title") or source.get("url", "the page")
    try:
        result = await llm_client.complete(
            f"Summarise the following page content in a few clear bullet points:\n\n{content}",
            system="You summarise web content faithfully. Do not invent facts.",
        )
        return f"📄 {title}\n\n{result.text}"
    except LLMError:
        return f"📄 {title}\n\n{content[:800]}"
