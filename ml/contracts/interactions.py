"""
ML Contract — Interaction Records & Dataset
=============================================
Defines the input contract for Collaborative Filtering (Phase 9).
These are the interaction signals that feed into matrix factorization
and similar user-item models.

INTERACTION WEIGHTS (configurable — these defaults are hypotheses, not facts):
  DO NOT hardcode these values in model implementations.
  Load them from config/ml_config.yaml to allow experimentation.

  play:           1.0   (implicit positive signal)
  complete:       2.0   (strong positive signal — listened to the end)
  like:           4.0   (explicit strong positive signal)
  playlist_add:   3.0   (strong intent signal)
  share:          3.5   (strong social signal)
  skip:          -1.0   (implicit negative signal)
  skip_early:    -2.0   (strong negative signal — skipped within first 30s)
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum

from ml.contracts.identifiers import UserId, SongId, SessionId


class InteractionType(str, Enum):
    PLAY            = "play"
    COMPLETE        = "complete"
    LIKE            = "like"
    PLAYLIST_ADD    = "playlist_add"
    SHARE           = "share"
    SKIP            = "skip"
    SKIP_EARLY      = "skip_early"


class InteractionRecord(BaseModel):
    """
    A single atomic user-song interaction event.
    This is the fundamental unit of the Collaborative Filtering dataset.

    Reuses song_id and user_id canonical identifiers.
    weight is pre-computed at ingestion using the InteractionWeightConfig.
    """
    user_id: UserId
    song_id: SongId
    interaction_type: InteractionType
    timestamp: datetime
    weight: float = Field(..., description="Pre-computed interaction weight from config")
    source: Optional[str] = Field(None, description="Origin of the dataset (e.g., 'lastfm', 'app')")
    session_id: Optional[SessionId] = None
    context_type: Optional[str] = None     # playlist | radio | search | recommendation


class InteractionWeightConfig(BaseModel):
    """
    Configurable weight mapping for all interaction types.
    Load this from config/ml_config.yaml — never hardcode weights.
    """
    play:          float = 1.0
    complete:      float = 2.0
    like:          float = 4.0
    playlist_add:  float = 3.0
    share:         float = 3.5
    skip:          float = -1.0
    skip_early:    float = -2.0

    def get_weight(self, interaction_type: InteractionType) -> float:
        return getattr(self, interaction_type.value, 0.0)


class InteractionDataset(BaseModel):
    """
    A versioned, bounded collection of InteractionRecords.
    Used as input to collaborative filtering training pipelines.
    """
    dataset_version: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    date_range_start: datetime
    date_range_end: datetime
    interactions: List[InteractionRecord]
    weight_config_version: str = Field(
        ..., description="Which InteractionWeightConfig version was used"
    )

    @property
    def record_count(self) -> int:
        return len(self.interactions)

    @property
    def unique_users(self) -> int:
        return len(set(r.user_id for r in self.interactions))

    @property
    def unique_songs(self) -> int:
        return len(set(r.song_id for r in self.interactions))


class UserItemMatrix(BaseModel):
    """
    A sparse representation of user-item interaction strengths.
    Constructed from an InteractionDataset before training.

    The actual matrix storage (scipy sparse, numpy, etc.) is an
    implementation detail of the Collaborative Filtering module.
    """
    dataset_version: str
    user_count: int
    item_count: int
    density: float = Field(..., description="Fraction of non-zero entries (0.0–1.0)")
    user_id_index: Dict[str, int]   # user_id → row index
    song_id_index: Dict[str, int]   # song_id → col index
    created_at: datetime = Field(default_factory=datetime.utcnow)
