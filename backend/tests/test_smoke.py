"""Smoke tests for Baghewala-X FastAPI backend."""
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_endpoint_smoke():
    """Verify backend health endpoint returns 200 OK and contains status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["ps_id"] == "SIH26120"

def test_api_ping_smoke():
    """Verify backend api ping router returns 200 OK with pong."""
    response = client.get("/api/ping")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "pong"
    assert "service" in data

def test_twin_run_smoke():
    """Verify the /api/twin/run endpoint runs a full simulation and returns a SOR value."""
    payload = {
        "well_id": "smoke-well",
        "steam_rate_tpd": 700.0,
        "steam_temp_c": 250.0,
        "injection_days": 10,
        "steam_quality": 0.80,
        "soak_days": 3,
        "production_days": 30,
        "spm": 5.0,
        "vfd_hz": 30.0,
        "water_cut_pct": 30.0,
        "oil_price_usd_bbl": 60.0,
        "steam_cost_usd_tonne": 12.0,
    }
    response = client.post("/api/twin/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["cycle_result"]["cycle_oil"] > 0
    assert data["cycle_result"]["SOR"] > 0
    assert data["economics"]["net_cash_flow_usd"] is not None
