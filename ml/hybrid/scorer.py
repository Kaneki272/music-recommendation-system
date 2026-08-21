import numpy as np
from typing import Dict, Any, List

class ScoreNormalizer:
    """Independent normalization logic for different model outputs."""
    
    def __init__(self, als_min: float = -1.0, als_max: float = 2.0, max_pop: float = 10000.0):
        self.als_min = als_min
        self.als_max = als_max
        self.max_pop = max_pop

    def normalize_als(self, raw_score: float) -> float:
        """Min-Max scale for ALS latent factor dot products. Clamped to [0, 1]."""
        norm = (raw_score - self.als_min) / (self.als_max - self.als_min) if self.als_max > self.als_min else 0.0
        return max(0.0, min(1.0, norm))

    def normalize_popularity(self, raw_score: float) -> float:
        """Logarithmic scaling for popularity counts to prevent massive skew."""
        # raw_score is play count
        num = np.log1p(raw_score)
        den = np.log1p(self.max_pop)
        norm = num / den if den > 0 else 0.0
        return max(0.0, min(1.0, norm))

    def normalize_content(self, raw_score: float) -> float:
        """Assuming cosine similarity for content, range is typically [-1, 1] or [0, 1]."""
        # If cosine similarity, map [-1, 1] to [0, 1]. 
        norm = (raw_score + 1.0) / 2.0
        return max(0.0, min(1.0, norm))

class HybridScorer:
    """Fuses normalized scores using dynamically renormalized weights."""
    
    @staticmethod
    def renormalize_weights(base_weights: Dict[str, float], available_models: List[str]) -> Dict[str, float]:
        """
        Adjusts weights when a model is missing.
        Example: ALS=0.6, Content=0.25, Pop=0.15. If Content unavailable (Sum = 0.75):
        ALS = 0.6/0.75 = 0.8, Pop = 0.15/0.75 = 0.2
        """
        active_weights = {m: w for m, w in base_weights.items() if m in available_models and w > 0}
        total_weight = sum(active_weights.values())
        
        if total_weight <= 0:
            return {m: 0.0 for m in available_models}
            
        return {m: w / total_weight for m, w in active_weights.items()}

    def score(self, 
              als_raw: float, 
              pop_raw: float, 
              content_raw: float, 
              weights: Dict[str, float],
              normalizer: ScoreNormalizer) -> Dict[str, Any]:
        """
        Computes the final hybrid score from available signals.
        Returns the final score and explainable contributions.
        """
        c_als = normalizer.normalize_als(als_raw) * weights.get("als", 0.0) if als_raw is not None else 0.0
        c_pop = normalizer.normalize_popularity(pop_raw) * weights.get("popularity", 0.0) if pop_raw is not None else 0.0
        c_content = normalizer.normalize_content(content_raw) * weights.get("content", 0.0) if content_raw is not None else 0.0
        
        final_score = c_als + c_pop + c_content
        
        return {
            "final_score": float(final_score),
            "contributions": {
                "als": float(c_als),
                "popularity": float(c_pop),
                "content": float(c_content)
            }
        }
