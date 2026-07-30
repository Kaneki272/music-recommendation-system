from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any

class ListeningHistory(BaseModel):
    user_id: str = Field(..., description="UUID of the user")
    song_id: str = Field(..., description="UUID of the song")
    played_at: datetime = Field(default_factory=datetime.utcnow)
    context: str = Field(..., description="Where it was played (e.g., search, playlist, recommendation)")
    duration_played_ms: int
    completion_rate: float = Field(..., ge=0.0, le=1.0)

class UserInteraction(BaseModel):
    user_id: str
    item_id: str = Field(..., description="UUID of song, album, or artist")
    item_type: str = Field(..., description="song, album, artist")
    interaction_type: str = Field(..., description="like, skip, share, add_to_playlist")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class RecommendationHistory(BaseModel):
    recommendation_id: str = Field(..., description="Unique ID for this served batch")
    user_id: str
    served_at: datetime = Field(default_factory=datetime.utcnow)
    algorithm_version: str
    candidate_song_ids: List[str]
    clicked_song_ids: List[str] = []

class UserPreference(BaseModel):
    user_id: str
    favorite_genres: List[str] = []
    favorite_artists: List[str] = []
    acoustic_preferences: Dict[str, float] = Field(
        default_factory=dict, 
        description="e.g., {'danceability': 0.8, 'energy': 0.7}"
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow)
