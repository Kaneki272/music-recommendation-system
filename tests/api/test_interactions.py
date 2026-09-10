import pytest
from fastapi.testclient import TestClient
from backend.main import app
import time

client = TestClient(app)

def test_post_interaction():
    """
    Test that submitting an interaction event returns success and pushes to Kafka.
    This test expects Kafka to be running.
    """
    payload = {
        "user_id": "user_000949",
        "song_id": "test_song_xyz",
        "interaction_type": "play",
        "weight": 1.0
    }
    
    with TestClient(app) as client:
        response = client.post("/api/v1/interactions/", json=payload)
        
    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()
    assert data["status"] == "success"
    assert "event_id" in data
