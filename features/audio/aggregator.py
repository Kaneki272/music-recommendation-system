"""
Module 5.4 — Feature Aggregator
==================================
Songs have variable duration, so time-series features (e.g., MFCCs
of shape [20, T]) cannot be stored directly. This module computes
statistical moments across the time axis to produce a single
fixed-length numerical vector per song.

Statistical moments computed per feature:
  - mean, std, min, max, median, skewness, kurtosis (7 stats)

Example:
  MFCC [20, T]  →  20 coefficients × 7 stats  =  140 values
  The full AudioFeatureVector has 193 dimensions.

Design contract:
  - Input:  RawFeatureSet (from DSPExtractor)
  - Output: AudioFeatureVector (fixed-length, ready for Qdrant)
  - No knowledge of storage, recommendations, or Kafka.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class AudioFeatureVector:
    """
    A fixed-length numerical representation of a song's acoustic identity.
    This is the primary artifact that powers Content-Based Filtering.

    Dimensionality breakdown:
      Rhythm   : tempo_bpm(1) + beat_count(1) + onset_mean(1)        =   3
      MFCC     : 20 coefficients × 7 stats                            = 140
      Centroid : 7 stats                                               =   7
      Rolloff  : 7 stats                                               =   7
      Bandwidth: 7 stats                                               =   7
      ZCR      : 7 stats                                               =   7
      RMS      : 7 stats                                               =   7
      Chroma   : 12 pitch classes × 2 stats (mean, std)               =  24
      Tonnetz  : 6 dimensions × 2 stats (mean, std)                   =  12
      Harmonic : harmonic_ratio(1)                                     =   1
                                                              Total = 222
    """
    song_id: str
    vector: List[float]                # Fixed-length feature vector
    vector_dimension: int              # Should always equal len(vector)
    tempo_bpm: float                   # Stored separately for fast filtering
    harmonic_ratio: float              # Stored separately for fast filtering
    extraction_version: str            # e.g., "v1.0.0" — for reprocessing logic


class FeatureAggregatorInterface(ABC):
    """Abstract base for converting time-series features to fixed vectors."""

    @abstractmethod
    def aggregate(self, raw_features: "RawFeatureSet") -> AudioFeatureVector:
        """
        Compute statistical moments across time axis for all features.
        Returns a fixed-length AudioFeatureVector.
        """
        pass
