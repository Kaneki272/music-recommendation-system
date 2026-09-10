import os
import json
from typing import Optional, List, Dict
from fastapi import APIRouter
from pydantic import BaseModel
import datetime
import random

from backend.api.v1.songs.router import get_audio_catalog

router = APIRouter()

INTERACTIONS_FILE = os.path.join(os.getcwd(), "datasets", "raw", "local_interactions.json")

# In-memory store
# user_id -> list of interactions
local_interactions = {}

def load_interactions():
    global local_interactions
    if os.path.exists(INTERACTIONS_FILE):
        try:
            with open(INTERACTIONS_FILE, "r") as f:
                local_interactions = json.load(f)
        except Exception:
            local_interactions = {}

def save_interactions():
    with open(INTERACTIONS_FILE, "w") as f:
        json.dump(local_interactions, f, indent=2)

# Load immediately
load_interactions()

class InteractionPayload(BaseModel):
    user_id: str
    song_id: str
    interaction_type: str
    timestamp: str
    weight: Optional[float] = 1.0

@router.post("/analytics/interaction")
async def log_interaction(payload: InteractionPayload):
    """Stores interactions locally"""
    if payload.user_id not in local_interactions:
        local_interactions[payload.user_id] = []
        
    local_interactions[payload.user_id].append({
        "song_id": payload.song_id,
        "type": payload.interaction_type.upper(),
        "timestamp": payload.timestamp
    })
    
    save_interactions()
    return {"success": True, "message": f"Interaction {payload.interaction_type} logged"}

@router.get("/recommendations/user/{user_id}")
async def get_user_recommendations(user_id: str, limit: int = 10):
    """Personalized recommendations without external DBs"""
    catalog = get_audio_catalog()
    
    # Get user history
    history = local_interactions.get(user_id, [])
    
    # Find skipped and liked songs
    skipped_songs = {i["song_id"] for i in history if i["type"] == "SKIP"}
    liked_songs = {i["song_id"] for i in history if i["type"] in ["LIKE", "PLAY"]}
    
    # Filter catalog
    available_songs = [s for s in catalog if s["song_id"] not in skipped_songs]
    
    # If we have less than limit, just return what we have
    if len(available_songs) == 0:
        return []
        
    # Basic personalization: sort so unplayed songs are mixed with liked artists
    # For now, just shuffle and return, since all songs are basically new, 
    # but ensure skipped songs are REMOVED (which they are)
    # Use user_id and history length to seed so it's stable until they interact
    random.seed(f"{user_id}_{len(history)}") 
    random.shuffle(available_songs)
    
    results = []
    for rank, s in enumerate(available_songs[:limit]):
        # Mock track response format
        results.append({
            "id": s["song_id"],
            "title": s["title"],
            "artist": {
                "id": f"artist_{s['artist']}",
                "name": s["artist"]
            },
            "album": {
                "id": f"album_{s['song_id']}",
                "title": "Local Album",
                "artist_id": f"artist_{s['artist']}",
                "cover_image_url": f"https://picsum.photos/seed/{s['song_id']}/300/300"
            },
            "duration_ms": 200000,
            "genres": ["Pop", "Electronic"],
            "audio_url": s["audio_url"],
            "match_score": 0.99 - (rank * 0.01),
            "recommendation_reason": "Based on your recent listening" if len(history) > 0 else "Trending Globally"
        })
        
    return results

@router.get("/songs/trending")
async def get_trending_songs():
    """Fallback trending endpoint"""
    return await get_user_recommendations("default_user", 10)
