"""Cost guard + per-user rate limiting.

Ported in spirit from the owner's Hermes `cost_guard.py`: track spend against a
daily budget, warn at 80%, hard-stop when exceeded. Here it is async and backed
by Redis (via src.core.store) with an in-process fallback, and it also enforces
a simple per-user requests-per-minute limit.

Budgets are enforced by TWO signals, whichever trips first:
  * daily token count vs DAILY_TOKEN_BUDGET
  * daily estimated USD vs DAILY_COST_BUDGET_USD
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from src.config import get_settings
from src.core import store
from src.core.logging import logger
from src.llm.pricing import estimate_usd

_DAY_SECONDS = 86_400


def _today() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


@dataclass
class GuardDecision:
    allowed: bool
    reason: str | None = None


async def check_rate(user_id: int) -> GuardDecision:
    """Per-user requests-per-minute limit."""
    settings = get_settings()
    minute = int(time.time() // 60)
    key = f"rl:{user_id}:{minute}"
    count = await store.incr_with_ttl(key, ttl_seconds=60)
    if count > settings.user_rate_per_min:
        return GuardDecision(False, "rate_limited")
    return GuardDecision(True)


async def check_budget() -> GuardDecision:
    """Global daily budget check (does not spend; just reads current totals)."""
    settings = get_settings()
    day = _today()
    tokens = await _read_counter(f"budget:tokens:{day}")
    cost_milli = await _read_counter(f"budget:costmilli:{day}")
    cost = cost_milli / 1000.0

    if tokens >= settings.daily_token_budget:
        logger.warning("daily token budget exceeded: {}/{}", tokens, settings.daily_token_budget)
        return GuardDecision(False, "token_budget_exceeded")
    if cost >= settings.daily_cost_budget_usd:
        logger.warning("daily cost budget exceeded: ${:.3f}/${}", cost, settings.daily_cost_budget_usd)
        return GuardDecision(False, "cost_budget_exceeded")
    return GuardDecision(True)


async def record(model: str, prompt_tokens: int, completion_tokens: int) -> None:
    """Add a completion's tokens + estimated cost to today's running totals."""
    day = _today()
    total_tokens = prompt_tokens + completion_tokens
    cost = estimate_usd(model, prompt_tokens, completion_tokens)
    # Cost stored in milli-USD so we can use integer counters.
    await store.incrby_with_ttl(f"budget:tokens:{day}", total_tokens, _DAY_SECONDS)
    await store.incrby_with_ttl(f"budget:costmilli:{day}", int(round(cost * 1000)), _DAY_SECONDS)


async def snapshot() -> dict:
    """Current-day usage vs budgets — for /stats and /budget."""
    settings = get_settings()
    day = _today()
    tokens = await _read_counter(f"budget:tokens:{day}")
    cost = await _read_counter(f"budget:costmilli:{day}") / 1000.0
    return {
        "date": day,
        "tokens": tokens,
        "token_budget": settings.daily_token_budget,
        "cost_usd": round(cost, 4),
        "cost_budget_usd": settings.daily_cost_budget_usd,
    }


async def _read_counter(key: str) -> int:
    # incrby of 0 returns the current value without changing it (and refreshes
    # only if it had to create the key, which incrby-by-0 won't meaningfully do).
    return await store.incrby_with_ttl(key, 0, _DAY_SECONDS)
