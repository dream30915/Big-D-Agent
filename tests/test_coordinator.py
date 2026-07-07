import pytest

from src.agent import coordinator
from src.agent.intent import Intent
from src.agent.specialists import SPECIALIST_NAME


def test_is_complex_short_message_is_simple():
    assert coordinator._is_complex("hello") is False


def test_is_complex_long_message():
    assert coordinator._is_complex("x " * 100) is True


def test_is_complex_multi_step_keyword():
    assert coordinator._is_complex("scrape the site then summarise it") is True


def test_is_complex_thai_keyword():
    assert coordinator._is_complex("ทำอันนี้ จากนั้นสรุปให้หน่อย") is True


def test_specialist_names_cover_all_intents():
    for intent in Intent:
        assert intent in SPECIALIST_NAME


async def test_run_returns_general_specialist_for_chat_offline():
    # No API key in tests → LLM specialist degrades gracefully (no exception).
    result = await coordinator.run("hi there", Intent.CHAT)
    assert result.specialist == "GeneralSpecialist"
    assert result.planned is False
    assert isinstance(result.text, str) and result.text
