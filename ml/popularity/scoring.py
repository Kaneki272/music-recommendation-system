"""
Popularity Scoring & Decay
==========================
Pure functions for calculating time-decayed interaction scores.
"""
import math
from datetime import datetime
from ml.contracts.interactions import InteractionRecord


def calculate_decay_multiplier(
    timestamp: datetime,
    reference_time: datetime,
    half_life_days: float
) -> float:
    """
    Calculates the exponential time-decay multiplier.
    Multiplier = 0.5 ^ (delta_days / half_life_days)
    Interactions in the future (relative to reference) return 0.
    """
    delta = (reference_time - timestamp).total_seconds()
    if delta < 0:
        return 0.0  # Cannot count future interactions (vital for temporal eval)
        
    delta_days = delta / (24 * 3600)
    
    # half_life_days = 0 means infinite decay (only immediate interactions count)
    if half_life_days <= 0:
        return 0.0 if delta_days > 0 else 1.0
        
    return math.pow(0.5, delta_days / half_life_days)


def calculate_decayed_weight(
    interaction: InteractionRecord,
    reference_time: datetime,
    half_life_days: float
) -> float:
    """
    Computes the final popularity contribution of a single interaction.
    """
    decay = calculate_decay_multiplier(
        timestamp=interaction.timestamp,
        reference_time=reference_time,
        half_life_days=half_life_days
    )
    return interaction.weight * decay
