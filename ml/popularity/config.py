"""
Popularity Model Configuration
==============================
Defines the configurable parameters for the popularity model.
"""
from pydantic import BaseModel, Field
from typing import Literal
from enum import Enum
from ml.contracts.interactions import InteractionWeightConfig


class PopularityMode(str, Enum):
    GLOBAL = "global"
    TRENDING = "trending"


class PopularityConfig(BaseModel):
    mode: PopularityMode = Field(
        default=PopularityMode.GLOBAL,
        description="Global uses a long half-life, Trending uses a short half-life."
    )
    half_life_days: float = Field(
        default=180.0,
        description="Time in days for an interaction's weight to decay by half."
    )
    normalizer_type: Literal["min_max", "rank"] = Field(
        default="min_max",
        description="Normalization strategy for scores."
    )
    weights: InteractionWeightConfig = Field(
        default_factory=InteractionWeightConfig,
        description="Weight definitions for each interaction type."
    )
