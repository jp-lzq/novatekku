from fastapi.testclient import TestClient

from app.main import app


def test_only_health_is_exposed() -> None:
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "healthy"}
        assert client.get("/openapi.json").status_code == 404
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/").status_code == 404
