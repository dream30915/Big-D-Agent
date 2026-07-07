"""Intent classification.

A fast, deterministic keyword pass handles the obvious cases for free (no token
spend). Anything ambiguous is left as CHAT, which the agent answers with the
LLM directly. This mirrors the plan's "Intent Classification" + "Cost
Optimization" goals: cheap routing first, model only when needed.
"""
from __future__ import annotations

import re
from enum import Enum


class Intent(str, Enum):
    SCRAPE = "scrape"
    BROWSE = "browse"
    CONTENT = "content"
    SUPPORT = "support"
    ANALYZE = "analyze"
    CHAT = "chat"


# Ordered rules — first match wins. English keywords use word boundaries; Thai
# keywords are matched as plain substrings (the \b word boundary does not work
# with Thai script, which has no ASCII word breaks).
_RULES: list[tuple[Intent, re.Pattern[str], tuple[str, ...]]] = [
    (Intent.SCRAPE, re.compile(r"\b(scrape|crawl|extract from|fetch url)\b", re.I),
     ("ดึงข้อมูลเว็บ", "ดึงเว็บ")),
    (Intent.BROWSE, re.compile(r"\b(browser|click|screenshot|automate)\b", re.I),
     ("เปิดเว็บ", "กดปุ่ม")),
    (Intent.CONTENT, re.compile(r"\b(write|draft|caption|blog|post)\b", re.I),
     ("เขียน", "แคปชั่น")),
    (Intent.SUPPORT, re.compile(r"\b(help me with|faq|ticket|refund|complaint)\b", re.I),
     ("ปัญหา", "คืนเงิน")),
    (Intent.ANALYZE, re.compile(r"\b(analyze|analyse|report|revenue|profit)\b", re.I),
     ("วิเคราะห์", "กำไร")),
]


def classify(text: str) -> Intent:
    """Return the best-guess intent for a message."""
    stripped = text.strip()
    if stripped.startswith("http://") or stripped.startswith("https://"):
        return Intent.SCRAPE
    for intent, pattern, thai_keywords in _RULES:
        if pattern.search(stripped) or any(k in stripped for k in thai_keywords):
            return intent
    return Intent.CHAT
