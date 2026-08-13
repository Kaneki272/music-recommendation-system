"""
ML Contract — Dataset Versioning
====================================
Every training dataset must be identified with a DatasetMetadata record.
This enables a trained model to precisely identify which data produced it.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from ml.contracts.identifiers import DatasetVersion


class DatasetMetadata(BaseModel):
    """
    Authoritative metadata for a versioned ML training dataset.
    Stored alongside model artifacts to ensure reproducibility.
    """
    dataset_name: str = Field(..., description="e.g., 'interaction_dataset', 'audio_features_v1'")
    dataset_version: DatasetVersion
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source: str = Field(..., description="e.g., 'mongodb.listening_history', 'postgresql.audio_features'")
    row_count: int
    unique_users: Optional[int] = None
    unique_songs: Optional[int] = None
    feature_version: str = Field(..., description="e.g., 'audio_v1.0.0'")
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    preprocessing_version: str = Field(..., description="e.g., 'preprocessor_v1.0.0'")
    notes: Optional[str] = None
