from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class BaseEvent(BaseModel):
    event_id: str = Field(..., description="Unique identifier for the event")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event generation timestamp")
    user_id: str = Field(..., description="User ID associated with the event")
    session_id: Optional[str] = Field(None, description="User session ID")

class SongPlayed(BaseEvent):
    song_id: str = Field(..., description="ID of the song played")
    context_type: str = Field(..., description="E.g., playlist, album, radio, search")
    context_id: Optional[str] = Field(None, description="ID of the context (e.g., playlist ID)")
    duration_played_ms: int = Field(..., description="Total milliseconds the song was played")
    completion_rate: float = Field(..., description="Percentage of song completed (0.0 to 1.0)")

class SongLiked(BaseEvent):
    song_id: str = Field(..., description="ID of the song liked")
    context_type: Optional[str] = Field(None, description="Context from where the song was liked")

class SongSkipped(BaseEvent):
    song_id: str = Field(..., description="ID of the song skipped")
    duration_played_ms: int = Field(..., description="How long it was played before skipping")
    skip_timestamp_ms: int = Field(..., description="Timestamp in the track where skip occurred")

class PlaylistCreated(BaseEvent):
    playlist_id: str = Field(..., description="ID of the newly created playlist")
    name: str = Field(..., description="Name of the playlist")
    initial_song_ids: List[str] = Field(default_factory=list, description="Initial songs added")

class RecommendationServed(BaseEvent):
    recommendation_id: str = Field(..., description="Unique ID for this recommendation batch")
    song_ids: List[str] = Field(..., description="List of songs presented to user")
    algorithm_version: str = Field(..., description="Version/name of algorithm used (e.g., hybrid_v2)")
    context: str = Field(..., description="Where it was served (e.g., home_feed, discovery_weekly)")

class RecommendationClicked(BaseEvent):
    recommendation_id: str = Field(..., description="ID of the recommendation batch")
    song_id: str = Field(..., description="The song that was clicked")
    position: int = Field(..., description="Index position of the clicked song in the served list")

class RecommendationIgnored(BaseEvent):
    recommendation_id: str = Field(..., description="ID of the recommendation batch ignored")
    time_visible_ms: int = Field(..., description="How long the recommendation was visible before being ignored")
