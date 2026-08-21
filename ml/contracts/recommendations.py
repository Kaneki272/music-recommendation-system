"""
ML Contract — Recommendation Output
=======================================
Defines the standardized output that EVERY recommendation model
must produce, regardless of algorithm.

CRITICAL RULE ON SCORES:
  A Content-Based score of 0.8 is NOT directly comparable to a
  Collaborative Filtering score of 0.8. Scores are model-specific.
  Raw scores MUST NOT be blended directly by the Hybrid Engine.
  Score normalization (Phase 10) bridges this gap.

FLOW:
  Model A (content_based)   → RecommendationScore(score=0.8)  ┐
  Model B (collaborative)   → RecommendationScore(score=0.71) ├→ ScoreNormalizer → CandidateSet → Hybrid Engine
  Model C (popularity)      → RecommendationScore(score=0.93) ┘
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

from ml.contracts.identifiers import SongId, UserId, ModelVersion


class RecommendationScore(BaseModel):
    """
    Standardized output from any single recommendation model.

    Every model — Popularity, Content-Based, Collaborative,
    or Hybrid — MUST return results in this format.
    """
    song_id: SongId
    score: float = Field(..., description="Raw model-specific score. NOT cross-model comparable.")
    model_name: str = Field(..., description="e.g., 'content_based', 'collaborative', 'popularity'")
    model_version: ModelVersion = Field(..., description="e.g., 'v1.2.0'")
    rank: int = Field(..., ge=1, description="1-based rank within this model's output")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Optional model-specific debug metadata"
    )
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class RecommendationRequest(BaseModel):
    """Input to any recommendation model's predict/recommend method."""
    user_id: UserId
    limit: int = Field(default=50, ge=1, le=500,
                       description="Max candidates to return. Not the final list size.")
    exclude_song_ids: List[SongId] = Field(
        default_factory=list,
        description="Songs already played/liked — exclude from results"
    )
    recently_played_song_ids: List[SongId] = Field(
        default_factory=list,
        description="Recently played songs to filter out"
    )
    blocked_song_ids: List[SongId] = Field(
        default_factory=list,
        description="Songs explicitly blocked by the user"
    )
    blocked_artist_ids: List[str] = Field(
        default_factory=list,
        description="Artists explicitly blocked by the user"
    )
    context_type: Optional[str] = Field(
        None, description="home_feed | discovery_weekly | radio | playlist"
    )
    session_id: Optional[str] = None


class RecommendationResponse(BaseModel):
    """Full recommendation response wrapping a ranked list of scores."""
    user_id: UserId
    recommendations: List[RecommendationScore]
    model_name: str
    model_version: ModelVersion
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    latency_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Model-level metadata, e.g., profile_state=COLD_START | SPARSE_PROFILE | NORMAL"
    )
