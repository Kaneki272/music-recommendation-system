"""
ML Contract — Model Metadata, Versioning & Cold Start States
==============================================================
Every trained recommendation model MUST produce a ModelMetadata
artifact alongside its model weights. This is the contract that
makes models auditable, comparable, and reproducible.

ARTIFACT DIRECTORY LAYOUT (enforced):
  models/
    content_based/
      v1/
        model/        ← weights, ONNX export, etc.
        config.yaml   ← hyperparameters used
        metadata.json ← ModelMetadata serialized
    collaborative/
      v1/ ...
      v2/ ...       ← old versions are NEVER deleted

COLD START STATES:
  The system must be aware of a user/song's lifecycle to route
  recommendations to the correct fallback model.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from ml.contracts.identifiers import ModelVersion, DatasetVersion


# ===========================================================
# MODEL METADATA
# ===========================================================
class ModelType(str, Enum):
    CONTENT_BASED   = "content_based"
    COLLABORATIVE   = "collaborative"
    POPULARITY      = "popularity"
    HYBRID          = "hybrid"
    RANKING         = "ranking"
    ONLINE_LEARNING = "online_learning"


class ModelMetadata(BaseModel):
    """
    Standardized metadata for every trained model artifact.
    Serialized to metadata.json in the model artifact directory.
    """
    model_name: str
    model_type: ModelType
    model_version: ModelVersion
    training_timestamp: datetime
    dataset_version: DatasetVersion
    feature_version: str = Field(
        ..., description="Version of features used, e.g., 'audio_v1.0.0'"
    )
    hyperparameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="All hyperparameters used during training"
    )
    training_parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="e.g., {'epochs': 10, 'batch_size': 256, 'optimizer': 'adam'}"
    )
    evaluation_metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="e.g., {'ndcg_at_10': 0.42, 'precision_at_10': 0.31}"
    )
    artifact_path: str = Field(
        ..., description="Relative path to model artifact directory, e.g., models/content_based/v1/"
    )
    code_version: str = Field(
        ..., description="Git commit SHA of the code used for training"
    )
    is_production: bool = Field(
        default=False,
        description="True if this model version is currently serving production traffic"
    )


# ===========================================================
# COLD START STATES
# ===========================================================
class UserState(str, Enum):
    NEW_USER       = "new_user"      # Zero interactions — full cold start
    SPARSE_USER    = "sparse_user"   # < 10 interactions — partial cold start
    RETURNING_USER = "returning_user"  # ≥ 10 interactions — full personalization


class SongState(str, Enum):
    NEW_SONG     = "new_song"      # Just ingested — no interaction data yet
    SPARSE_SONG  = "sparse_song"   # < 10 interactions — limited signal
    CATALOG_SONG = "catalog_song"  # ≥ 10 interactions — full signal


class ColdStartContext(BaseModel):
    """
    Provides the Hybrid Engine with cold start awareness for routing.
    The engine uses this to decide which fallback models to invoke.
    """
    user_id: str
    user_state: UserState
    interaction_count: int

    def requires_popularity_fallback(self) -> bool:
        return self.user_state == UserState.NEW_USER

    def requires_content_fallback(self) -> bool:
        return self.user_state in (UserState.NEW_USER, UserState.SPARSE_USER)

    def allows_collaborative(self) -> bool:
        return self.user_state == UserState.RETURNING_USER
