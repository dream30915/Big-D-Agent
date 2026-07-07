import pytest

from src.core import memory, store


@pytest.fixture(autouse=True)
def _clear_store():
    store._mem_lists.clear()
    store._mem_counters.clear()
    yield
    store._mem_lists.clear()
    store._mem_counters.clear()


async def test_remember_then_recent_is_chronological():
    uid = 42
    await memory.remember(uid, "hello", "hi there")
    await memory.remember(uid, "how are you", "great")
    turns = await memory.recent(uid)
    assert [t["u"] for t in turns] == ["hello", "how are you"]
    assert turns[-1]["a"] == "great"


async def test_memory_is_capped_to_turns():
    uid = 7
    for i in range(20):
        await memory.remember(uid, f"q{i}", f"a{i}")
    turns = await memory.recent(uid)
    from src.config import get_settings

    assert len(turns) <= get_settings().memory_turns


async def test_as_context_empty_when_no_history():
    assert await memory.as_context(123456) == ""
