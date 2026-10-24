from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_success() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "one-bad-tuesday-api",
        "integrations": {"nessie": False, "serpapi": False, "gemini": False},
    }
