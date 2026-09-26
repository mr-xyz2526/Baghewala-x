"""Smoke tests for Baghewala-X FastAPI backend."""
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_endpoint_smoke():
    """Verify backend health endpoint returns 200 OK with expected payload."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_api_ping_smoke():
    """Verify backend api ping router returns 200 OK with pong."""
    response = client.get("/api/ping")
    assert response.status_code == 200
    assert response.json() == {"message": "pong"}
