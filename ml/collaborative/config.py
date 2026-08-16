from pydantic import BaseModel, Field
from typing import Dict, Optional

class InteractionWeightsConfig(BaseModel):
    """Configures positive feedback weights for the implicit ALS matrix."""
    play: float = 1.0
    complete: float = 2.0
    playlist_add: float = 3.0
    like: float = 4.0
    
    # We do NOT include skip directly in the ALS matrix formulation here
    # as ALS requires positive confidence. If skip-negative sampling is 
    # experimented with later, it is handled in a separate pipeline stage.
    
    def get_weight(self, interaction_type: str) -> float:
        return getattr(self, interaction_type, 0.0)

class ALSConfig(BaseModel):
    """ALS algorithm hyperparameters."""
    factors: int = 64
    regularization: float = 0.01
    iterations: int = 15
    alpha: float = 1.0  # Confidence scaling factor (Confidence = 1 + alpha * weight)
    random_state: int = 42
    use_gpu: bool = False
    
    def to_dict(self) -> dict:
        return {
            "factors": self.factors,
            "regularization": self.regularization,
            "iterations": self.iterations,
            "random_state": self.random_state,
            "use_gpu": self.use_gpu
        }
