"""
User Taste Profiler
===================
Constructs a single 222-dimensional dense vector representing a user's taste
by taking a time-decayed, weighted aggregation of their listening history.
"""
import math
from datetime import datetime
from typing import List, Optional

from ml.contracts.interactions import InteractionRecord
from ml.contracts.audio import AudioFeatureVector
from ml.contracts.identifiers import CANONICAL_VECTOR_DIMENSION


class UserTasteProfiler:
    def __init__(self, half_life_days: float):
        self.half_life_days = half_life_days

    def _calculate_decay(self, timestamp: datetime, reference_time: datetime) -> float:
        delta_seconds = (reference_time - timestamp).total_seconds()
        if delta_seconds < 0:
            return 0.0  # Strict temporal cutoff: no future data allowed
        
        delta_days = delta_seconds / (24 * 3600)
        if self.half_life_days <= 0:
            return 0.0 if delta_days > 0 else 1.0
            
        return math.pow(0.5, delta_days / self.half_life_days)

    def generate_profile(
        self,
        interactions: List[InteractionRecord],
        audio_features: List[AudioFeatureVector],
        reference_time: datetime
    ) -> Optional[List[float]]:
        """
        Calculates UserTasteVector = 
            Σ(interaction_weight * time_decay * audio_vector) / Σ(interaction_weight * time_decay)
        """
        if not interactions or not audio_features:
            return None

        # Create a lookup mapping song_id -> vector
        vector_map = {feat.song_id: feat.audio_feature_vector for feat in audio_features}
        
        aggregated_vector = [0.0] * CANONICAL_VECTOR_DIMENSION
        total_weight = 0.0
        
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
            
        if total_weight == 0.0:
            return None
            
        # Normalize by total weight
        for i in range(CANONICAL_VECTOR_DIMENSION):
            aggregated_vector[i] /= total_weight
            
        return aggregated_vector
