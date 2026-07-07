from fastapi.testclient import TestClient

from src.api.app import app

client = TestClient(app)


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_usage_shape():
    resp = client.get("/usage")
    assert resp.status_code == 200
    assert set(resp.json()) >= {"requests", "total_tokens"}
