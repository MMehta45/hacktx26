from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_success() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "one-bad-tuesday-api",
        "api_version": "0.4.1",
        "capabilities": {
            "research": True,
            "recovery_sessions": True,
            "targeted_research": True,
        },
        "integrations": {"nessie": False, "serpapi": False, "gemini": False},
    }
