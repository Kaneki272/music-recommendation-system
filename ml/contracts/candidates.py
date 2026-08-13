"""
ML Contract — Candidate Set
==============================
A CandidateSong can originate from multiple models simultaneously.
The Hybrid Engine receives a CandidateSet and resolves multi-model
scores for the same song during the fusion step (Phase 10).

Example:
  Song A appears in BOTH content_based AND collaborative outputs:
    CandidateSong(
      song_id="abc",
      source_scores={
        "content_based":  {"raw": 0.82, "normalized": 0.74},
        "collaborative":  {"raw": 0.71, "normalized": 0.68},
      }
    )
"""
from pydantic import BaseModel, Field
from typing import Dict, Optional, List
from datetime import datetime

from ml.contracts.identifiers import SongId, ModelVersion


class SourceScore(BaseModel):
    """A single model's contribution to a candidate's score."""
    model_name: str
    model_version: ModelVersion
    raw_score: float
    normalized_score: Optional[float] = Field(
        None, description="Populated after ScoreNormalizer runs"
    )


class CandidateSong(BaseModel):
    """
    A song candidate with scores from one or more source models.
    The Hybrid Engine reads source_scores to blend and produce a final rank.
    """
    song_id: SongId
    source_scores: Dict[str, SourceScore] = Field(
        default_factory=dict,
        description="Keyed by model_name. A song may appear in multiple models' outputs."
    )
    final_score: Optional[float] = Field(
        None, description="Populated by the Hybrid Engine after fusion"
    )
    final_rank: Optional[int] = Field(
        None, description="Populated by the Ranker after LTR (Phase 13)"
    )

    @property
    def source_model_names(self) -> List[str]:
        return list(self.source_scores.keys())

    @property
    def is_multi_source(self) -> bool:
        """True if the candidate was surfaced by more than one model."""
        return len(self.source_scores) > 1


class CandidateSet(BaseModel):
    """
    The complete pool of candidates passed to the Hybrid Engine.
    Produced by merging outputs from all active recommendation models.
    """
    user_id: str
    candidates: List[CandidateSong]
    assembled_at: datetime = Field(default_factory=datetime.utcnow)
    source_models: List[str] = Field(
        ..., description="Which models contributed to this candidate set"
    )

    @property
    def size(self) -> int:
        return len(self.candidates)

    def get_candidate(self, song_id: SongId) -> Optional[CandidateSong]:
        for c in self.candidates:
            if c.song_id == song_id:
                return c
        return None
