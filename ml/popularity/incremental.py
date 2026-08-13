"""
Popularity State Updater
========================
Abstraction for future Kafka integration. Allows online updates
to popularity scores without retraining the entire dataset.
"""
from typing import Dict
from datetime import datetime
from ml.contracts.identifiers import SongId
from ml.contracts.interactions import InteractionRecord
from ml.popularity.scoring import calculate_decay_multiplier


class PopularityStateUpdater:
    """
    Maintains incremental running scores for songs.
    Future Kafka consumers will call `record_interaction` upon receiving an event.
    """
    def __init__(self, half_life_days: float, reference_time: datetime):
        self.half_life_days = half_life_days
        self.reference_time = reference_time
        self.scores: Dict[SongId, float] = {}
        
    def record_interaction(self, interaction: InteractionRecord) -> None:
        """Process a single real-time interaction event."""
        decay = calculate_decay_multiplier(
            timestamp=interaction.timestamp,
            reference_time=self.reference_time,
            half_life_days=self.half_life_days
        )
        contribution = interaction.weight * decay
        
        current_score = self.scores.get(interaction.song_id, 0.0)
        self.scores[interaction.song_id] = current_score + contribution

    def get_top_k(self, k: int) -> Dict[SongId, float]:
        """Returns the top K songs by incremental score."""
        sorted_scores = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_scores[:k])
