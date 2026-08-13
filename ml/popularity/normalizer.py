"""
Score Normalizers
=================
Implementations of ScoreNormalizerInterface for Popularity scores.
"""
from typing import List
from ml.interfaces.score_normalizer import ScoreNormalizerInterface
from ml.contracts.recommendations import RecommendationScore


class MinMaxNormalizer(ScoreNormalizerInterface):
    """Scales scores linearly to the [0.0, 1.0] range."""
    def __init__(self):
        self.min_val = 0.0
        self.max_val = 1.0
        self.is_fitted = False

    def fit(self, scores: List[RecommendationScore]) -> None:
        if not scores:
            self.min_val = 0.0
            self.max_val = 1.0
            self.is_fitted = True
            return
            
        raw_scores = [s.score for s in scores]
        self.min_val = min(raw_scores)
        self.max_val = max(raw_scores)
        if self.min_val == self.max_val:
            self.max_val = self.min_val + 1.0
        self.is_fitted = True

    def normalize(self, scores: List[RecommendationScore]) -> List[RecommendationScore]:
        if not self.is_fitted:
            self.fit(scores)
            
        normalized = []
        for s in scores:
            new_score = s.model_copy()
            new_score.score = (s.score - self.min_val) / (self.max_val - self.min_val)
            # Clip to [0, 1] in case of unseen values during inference
            new_score.score = max(0.0, min(1.0, new_score.score))
            normalized.append(new_score)
        return normalized


class RankNormalizer(ScoreNormalizerInterface):
    """
    Normalizes by converting rank to a percentile [0.0, 1.0].
    Rank 1 = 1.0, Rank N = 0.0
    """
    def __init__(self):
        self.total_items = 1
        
    def fit(self, scores: List[RecommendationScore]) -> None:
        self.total_items = max(1, len(scores))

    def normalize(self, scores: List[RecommendationScore]) -> List[RecommendationScore]:
        if not scores:
            return []
            
        total = max(self.total_items, len(scores))
        normalized = []
        for s in scores:
            new_score = s.model_copy()
            # Rank 1 gets 1.0, Rank N gets ~0.0
            new_score.score = (total - s.rank + 1) / total
            normalized.append(new_score)
        return normalized


def get_normalizer(normalizer_type: str) -> ScoreNormalizerInterface:
    if normalizer_type == "min_max":
        return MinMaxNormalizer()
    elif normalizer_type == "rank":
        return RankNormalizer()
    else:
        raise ValueError(f"Unknown normalizer type: {normalizer_type}")
