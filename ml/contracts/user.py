"""
ML Contract — User Feature Representation
============================================
Defines the standardized user representation consumed by
Collaborative Filtering (Phase 9) and the Hybrid Engine (Phase 10).

DO NOT compute user embeddings here.
This defines ONLY the input contract.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

from ml.contracts.identifiers import UserId, SongId, ArtistId, SessionId


class SessionContext(BaseModel):
    """Ephemeral context about the user's current listening session."""
    session_id: SessionId
    started_at: datetime
    device_type: Optional[str] = None          # mobile | desktop | smart_speaker
    recently_played_in_session: List[SongId] = Field(default_factory=list)
    current_context_type: Optional[str] = None # playlist | album | radio | search


class UserRepresentation(BaseModel):
    """
    The canonical input to any model that needs to understand a user.

    ALL behavioral fields are Optional to support:
      - New users (cold start): only user_id is guaranteed
      - Returning users: full history available
      - Sparse users: partial history available

    The consuming model MUST handle any combination of missing fields.
    """
    user_id: UserId

    # ── Long-term behavioral signals ───────────────────────────
    recently_played: List[SongId]          = Field(default_factory=list)
    liked_songs: List[SongId]              = Field(default_factory=list)
    skipped_songs: List[SongId]            = Field(default_factory=list)
    playlist_songs: List[SongId]           = Field(default_factory=list)
    favorite_artists: List[ArtistId]       = Field(default_factory=list)
    favorite_genres: List[str]             = Field(default_factory=list)
    listening_history_count: int           = 0   # Total songs ever played

    # ── Acoustic preference fingerprint ────────────────────────
    acoustic_preferences: Dict[str, float] = Field(
        default_factory=dict,
        description="Aggregated acoustic preferences, e.g., {'tempo_bpm_mean': 128.0}"
    )

    # ── Session context (ephemeral) ────────────────────────────
    session_context: Optional[SessionContext] = None

    @property
    def is_new_user(self) -> bool:
        """True if the user has no interaction history (cold start)."""
        return self.listening_history_count == 0

    @property
    def is_sparse_user(self, threshold: int = 10) -> bool:
        """True if the user has minimal interaction history."""
        return 0 < self.listening_history_count < threshold
