from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.health import router


def test_health_endpoint() -> None:
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
