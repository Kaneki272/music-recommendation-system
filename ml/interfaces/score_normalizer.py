"""
ML Interface — Score Normalizer
==================================
The Hybrid Engine MUST NOT blend raw model scores directly.
Scores from different models are NOT on the same scale.

This interface defines the contract that any normalization
strategy must satisfy. The Hybrid Engine (Phase 10) depends
on this interface, not any concrete implementation.

Supported strategies (to be chosen via config/experimentation):
  - MinMaxNormalizer      : scales scores to [0, 1]
  - ZScoreNormalizer      : standardizes to mean=0, std=1
  - SoftmaxNormalizer     : converts scores to probabilities
  - RankNormalizer        : replaces scores with rank-based values
  - LearnedNormalizer     : calibrated via supervised training (advanced)
"""
from abc import ABC, abstractmethod
from typing import List

from ml.contracts.recommendations import RecommendationScore
from ml.contracts.candidates import CandidateSong


class ScoreNormalizerInterface(ABC):
    """Normalizes model-specific scores to a common comparable scale."""

    @abstractmethod
    def normalize(self, scores: List[RecommendationScore]) -> List[RecommendationScore]:
        """
        Normalize a list of scores from a SINGLE model.
        Input:  Raw RecommendationScore list from one model
        Output: Same list with scores replaced by normalized values
        """
        pass

    @abstractmethod
    def fit(self, scores: List[RecommendationScore]) -> None:
        """
        Fit normalization parameters (e.g., min/max, mean/std)
        from a reference score distribution. Required by
        MinMax and ZScore strategies; no-op for Rank and Softmax.
        """
        pass
