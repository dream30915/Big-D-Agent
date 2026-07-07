import pytest

from src.integrations import n8n


def test_build_payload_minimal():
    p = n8n.build_payload("hello", source="api")
    assert p == {"source": "api", "text": "hello"}


def test_build_payload_full():
    p = n8n.build_payload(
        "run report", user_id=5, chat_id=9, source="telegram", extra={"priority": "high"}
    )
    assert p["user_id"] == 5
    assert p["chat_id"] == 9
    assert p["source"] == "telegram"
    assert p["priority"] == "high"


async def test_trigger_reports_not_configured():
    # No N8N_WEBHOOK_URL in the test env → graceful, no network call, no raise.
    result = await n8n.trigger(n8n.build_payload("hi"))
    assert result.ok is False
    assert "not configured" in result.detail
