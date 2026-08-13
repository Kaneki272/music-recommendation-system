"""
Module 5.5 — Audio Feature Schema
====================================
Pydantic models defining the exact shape of AudioFeatureData
for persistence (PostgreSQL) and vector search (Qdrant payload).
These are the source-of-truth contracts for downstream consumers.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class AudioFeatureCreate(BaseModel):
    """Used when writing freshly extracted features to the database."""
    song_id: str
    vector: List[float]
    vector_dimension: int
    tempo_bpm: float
    harmonic_ratio: float
    extraction_version: str


class AudioFeatureRead(AudioFeatureCreate):
    """Used when reading features back from the database or Qdrant."""
    id: str
    extracted_at: datetime
    is_valid: bool

    class Config:
        from_attributes = True


class ExtractionJobStatus(BaseModel):
    """Tracks the status of a batch audio extraction run."""
    job_id: str
    total_songs: int
    processed: int = 0
    failed: int = 0
    status: str = "PENDING"          # PENDING | RUNNING | COMPLETED | FAILED
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_log: Optional[str] = None
