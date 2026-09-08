import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_get_recommendations_integration_known_user():
    """
    Integration test for the hybrid recommendation endpoint for a KNOWN_USER.
    """
    with TestClient(app) as client:
        response = client.get("/api/v1/recommendations/?user_id=user_000949&limit=5")
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code} with detail: {response.text}"
    
    data = response.json()
    assert data["user_id"] == "user_000949"
    assert "recommendations" in data
    assert data["metadata"]["user_state"] == "KNOWN_USER"
    assert data["metadata"]["active_weights"].get("popularity", 1.0) != 1.0 # Should not be 100% popularity
    
    recs = data["recommendations"]
    assert isinstance(recs, list)
    if len(recs) > 0:
        assert "song_id" in recs[0]
        ranks = [r["rank"] for r in recs]
        assert ranks == sorted(ranks), "Recommendations are not ranked correctly"

def test_get_recommendations_integration_new_user():
    """
    Integration test for the hybrid recommendation endpoint for a NEW_USER.
    """
    with TestClient(app) as client:
        response = client.get("/api/v1/recommendations/?user_id=user_unknown&limit=5")
    assert response.status_code == 200
    
    data = response.json()
    assert data["user_id"] == "user_unknown"
    assert data["metadata"]["user_state"] == "NEW_USER"
    assert data["metadata"]["active_weights"].get("popularity", 0.0) == 1.0
