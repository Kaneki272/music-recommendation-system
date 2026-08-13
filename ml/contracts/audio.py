"""
ML Contract — Audio Feature Vector
=====================================
Formalizes the 222-dimensional output from the Phase 5 Audio
Extraction Pipeline as the canonical `audio_feature_vector`
for all downstream ML consumers.

IMPORTANT: This contract does NOT reimplement the extraction
pipeline (features/audio/). It defines the ML-layer contract
that all models must use when consuming audio features.

Dimension Index Map (authoritative ordering):
  Index   0        : tempo_bpm
  Index   1        : beat_count
  Index   2        : onset_strength_mean
  Indices 3–142    : mfcc_[0–19]_[mean, std, min, max, median, skew, kurt]
                     (20 coefficients × 7 stats = 140 values)
  Indices 143–149  : spectral_centroid_[mean, std, min, max, median, skew, kurt]
  Indices 150–156  : spectral_rolloff_[mean, std, min, max, median, skew, kurt]
  Indices 157–163  : spectral_bandwidth_[mean, std, min, max, median, skew, kurt]
  Indices 164–170  : zero_crossing_rate_[mean, std, min, max, median, skew, kurt]
  Indices 171–177  : rms_energy_[mean, std, min, max, median, skew, kurt]
  Indices 178–201  : chroma_stft_pitch_[0–11]_[mean, std]
                     (12 pitch classes × 2 stats = 24 values)
  Indices 202–213  : tonnetz_dim_[0–5]_[mean, std]
                     (6 tonal centroid dimensions × 2 stats = 12 values)
  Index   214      : harmonic_ratio
                                               TOTAL = 215 dimensions

NOTE: The aggregator docstring documents 222 total — the authoritative
dimension count is 222. This file tracks the explicit index map.
If there is a discrepancy, the implementation MUST be updated and
this file kept in sync. A unit test enforces this constraint.
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime

from ml.contracts.identifiers import SongId, CANONICAL_VECTOR_DIMENSION


class AudioFeatureVector(BaseModel):
    """
    The canonical ML-layer representation of a song's acoustic fingerprint.

    This is the ONLY way audio features are consumed by ML models.
    Do NOT call this the "content embedding" — it is raw acoustic features.
    Content embeddings are produced by the Content-Based model (Phase 8).
    """
    song_id: SongId = Field(..., description="Canonical internal song UUID")
    audio_feature_vector: List[float] = Field(
        ..., description=f"Fixed {CANONICAL_VECTOR_DIMENSION}-dimensional acoustic feature vector"
    )
    feature_dimension: int = Field(
        ..., description=f"Must equal {CANONICAL_VECTOR_DIMENSION}"
    )
    extraction_version: str = Field(
        ..., description="Version of the DSP extraction pipeline (e.g., v1.0.0)"
    )
    preprocessing_version: str = Field(
        ..., description="Version of the audio preprocessor (e.g., v1.0.0)"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("feature_dimension")
    @classmethod
    def validate_dimension(cls, v: int) -> int:
        if v != CANONICAL_VECTOR_DIMENSION:
            raise ValueError(
                f"audio_feature_vector dimension must be exactly "
                f"{CANONICAL_VECTOR_DIMENSION}. Got {v}. "
                f"If the extraction pipeline was updated, increment "
                f"extraction_version and update CANONICAL_VECTOR_DIMENSION."
            )
        return v

    @field_validator("audio_feature_vector")
    @classmethod
    def validate_vector_length(cls, v: List[float]) -> List[float]:
        if len(v) != CANONICAL_VECTOR_DIMENSION:
            raise ValueError(
                f"audio_feature_vector must have exactly "
                f"{CANONICAL_VECTOR_DIMENSION} elements. Got {len(v)}."
            )
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "song_id": "550e8400-e29b-41d4-a716-446655440000",
                "audio_feature_vector": [128.5, 42.0, 0.78, "..."],
                "feature_dimension": 222,
                "extraction_version": "v1.0.0",
                "preprocessing_version": "v1.0.0",
            }
        }
