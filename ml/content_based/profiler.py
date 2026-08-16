"""
User Taste Profiler
===================
Constructs a single 222-dimensional dense vector representing a user's taste
by taking a time-decayed, weighted aggregation of their listening history.

Decay Formula:
    lambda = ln(2) / half_life_days
    weight(t) = exp(-lambda * delta_days)

This is the canonical exponential decay: at t = half_life_days, weight = 0.5.
"""
import math
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional

from ml.contracts.interactions import InteractionRecord
from ml.contracts.audio import AudioFeatureVector
from ml.contracts.identifiers import CANONICAL_VECTOR_DIMENSION


class ProfileState(str, Enum):
    """
    Explicit state of a user's taste profile.

    NORMAL        — User has enough interactions (>= minimum_interaction_threshold)
                    to construct a meaningful taste vector.
    SPARSE_PROFILE — User has some interactions, but below the minimum threshold.
                    This is a known-degraded state: results will be low-quality.
                    The Hybrid Engine should heavily discount this model's output.
    COLD_START    — User has zero interactions, or all interactions were in the future.
                    Content-Based cannot produce any recommendations. The Hybrid Engine
                    must fall back entirely to Popularity.
    """
    NORMAL = "NORMAL"
    SPARSE_PROFILE = "SPARSE_PROFILE"
    COLD_START = "COLD_START"


@dataclass
class ProfileResult:
    """
    The result of generating a user taste profile.
    Always check `state` before consuming `vector`.
    """
    state: ProfileState
    vector: Optional[List[float]] = None
    valid_interaction_count: int = 0
    total_weight: float = 0.0


class UserTasteProfiler:
    def __init__(self, half_life_days: float, minimum_interaction_threshold: int = 3):
        self.half_life_days = half_life_days
        self.minimum_interaction_threshold = minimum_interaction_threshold

        # Precompute decay constant: lambda = ln(2) / half_life
        if half_life_days > 0:
            self._lambda = math.log(2) / half_life_days
        else:
            self._lambda = None  # Signals "no decay" (weight = 1.0 at t=0, 0.0 otherwise)

    def _calculate_decay(self, timestamp: datetime, reference_time: datetime) -> float:
        """
        Returns the exponential decay weight for an interaction at `timestamp`
        relative to `reference_time`.

        Any interaction in the future (timestamp > reference_time) returns 0.0,
        enforcing strict temporal cutoff.
        """
        delta_seconds = (reference_time - timestamp).total_seconds()
        if delta_seconds < 0:
            return 0.0  # Strict temporal cutoff: no future data allowed

        delta_days = delta_seconds / (24 * 3600)

        if self._lambda is None:
            # No decay: treat all past interactions equally (delta_days == 0 => 1.0)
            return 1.0 if delta_days == 0 else 0.0

        return math.exp(-self._lambda * delta_days)

    def generate_profile(
        self,
        interactions: List[InteractionRecord],
        audio_features: List[AudioFeatureVector],
        reference_time: datetime
    ) -> ProfileResult:
        """
        Calculates UserTasteVector =
            Σ(interaction_weight × time_decay × audio_vector) / Σ(interaction_weight × time_decay)

        Returns a ProfileResult with an explicit state:
          - COLD_START        if no interactions provided or all decay to zero weight.
          - SPARSE_PROFILE    if valid interaction count < minimum_interaction_threshold.
          - NORMAL            otherwise.
        """
        if not interactions:
            return ProfileResult(state=ProfileState.COLD_START)

        # Create a lookup mapping song_id -> vector
        vector_map = {feat.song_id: feat.audio_feature_vector for feat in audio_features}

        aggregated_vector = [0.0] * CANONICAL_VECTOR_DIMENSION
        total_weight = 0.0
        valid_interaction_count = 0

        for interaction in interactions:
            vector = vector_map.get(interaction.song_id)
            if not vector:
                continue

            decay = self._calculate_decay(interaction.timestamp, reference_time)
            effective_weight = interaction.weight * decay

            if effective_weight <= 0:
                continue

            for i in range(CANONICAL_VECTOR_DIMENSION):
                aggregated_vector[i] += vector[i] * effective_weight

            total_weight += effective_weight
            valid_interaction_count += 1

        # COLD_START: no valid interactions contributed weight
        if total_weight == 0.0 or valid_interaction_count == 0:
            return ProfileResult(state=ProfileState.COLD_START)

        # Normalize by total weight
        normalized_vector = [v / total_weight for v in aggregated_vector]

        # SPARSE_PROFILE: interaction count is below minimum threshold
        if valid_interaction_count < self.minimum_interaction_threshold:
            return ProfileResult(
                state=ProfileState.SPARSE_PROFILE,
                vector=normalized_vector,
                valid_interaction_count=valid_interaction_count,
                total_weight=total_weight
            )

        return ProfileResult(
            state=ProfileState.NORMAL,
            vector=normalized_vector,
            valid_interaction_count=valid_interaction_count,
            total_weight=total_weight
        )
