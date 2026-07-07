import pytest

from src.config import get_settings
from src.core import costguard, store


@pytest.fixture(autouse=True)
def _clear_store():
    # Isolate each test from the in-process fallback counters.
    store._mem_counters.clear()
    store._mem_lists.clear()
    yield
    store._mem_counters.clear()
    store._mem_lists.clear()


async def test_rate_limit_trips_after_threshold():
    limit = get_settings().user_rate_per_min
    uid = 999
    for _ in range(limit):
        assert (await costguard.check_rate(uid)).allowed is True
    # The next one over the limit is refused.
    blocked = await costguard.check_rate(uid)
    assert blocked.allowed is False
    assert blocked.reason == "rate_limited"


async def test_budget_blocks_when_tokens_exceeded():
    assert (await costguard.check_budget()).allowed is True
    budget = get_settings().daily_token_budget
    await costguard.record("openai/gpt-4o-mini", budget, 0)
    decision = await costguard.check_budget()
    assert decision.allowed is False
    assert decision.reason == "token_budget_exceeded"


async def test_snapshot_reports_usage():
    await costguard.record("openai/gpt-4o-mini", 1000, 500)
    snap = await costguard.snapshot()
    assert snap["tokens"] == 1500
    assert snap["cost_usd"] >= 0
