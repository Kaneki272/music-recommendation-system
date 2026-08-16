"""
Content-Based Model Configuration
=================================
Configures weights for user profiling and multi-modal similarity scoring.
All weights are EXPERIMENTAL and NOT final. Each named configuration
represents a hypothesis to be validated via ablation evaluation.
"""
from enum import Enum
from pydantic import BaseModel, Field
from ml.contracts.interactions import InteractionWeightConfig


class SimilarityWeights(BaseModel):
    """Controls how much each modality contributes to the final score."""
    audio_weight: float = 1.0
    genre_weight: float = 0.5
    artist_weight: float = 0.2


class ContentBasedConfig(BaseModel):
    similarity_weights: SimilarityWeights = Field(default_factory=SimilarityWeights)
    profiler_half_life_days: float = Field(
        default=30.0,
        description="Half-life for decaying older user interactions. Used to derive lambda = ln(2)/half_life."
    )
    interaction_weights: InteractionWeightConfig = Field(default_factory=InteractionWeightConfig)
    retrieval_candidate_pool_multiplier: int = Field(
        default=3,
        description="If requesting K recommendations, retrieve K * Multiplier candidates from Qdrant before metadata filtering."
    )
    minimum_interaction_threshold: int = Field(
        default=3,
        description=(
            "Minimum number of valid (non-zero-weight) interactions required to construct a "
            "normal user taste profile. Users below this threshold receive a SPARSE_PROFILE state."
        )
    )
