"""
ML Interface — Recommendation Model
=======================================
The abstract base class that EVERY recommendation model must implement.

Covered by this interface:
  - Popularity Model (Phase 7)
  - Content-Based Model (Phase 8)
  - Collaborative Filtering Model (Phase 9)
  - Hybrid Engine (Phase 10)
  - Ranking Model (Phase 13)

Design philosophy:
  The interface enforces a consistent external contract.
  It does NOT dictate internal implementation (matrix factorization,
  cosine similarity, XGBoost — all are valid internals).
"""
from abc import ABC, abstractmethod
from typing import List

from ml.contracts.recommendations import RecommendationRequest, RecommendationResponse
from ml.contracts.models import ModelMetadata


class RecommendationModelInterface(ABC):
    """Abstract base for all recommendation models in the system."""

    @abstractmethod
    async def train(self, dataset_version: str, **kwargs) -> ModelMetadata:
        """
        Train or retrain the model on the specified dataset version.
        Returns ModelMetadata describing the produced artifact.
        """
        pass

    @abstractmethod
    async def predict(self, request: RecommendationRequest) -> RecommendationResponse:
        """
        Generate ranked recommendations for a single user request.
        Must return RecommendationResponse — never a raw list.
        """
        pass

    @abstractmethod
    async def save(self, artifact_path: str) -> None:
        """Serialize model weights and config to the artifact path."""
        pass

    @abstractmethod
    async def load(self, artifact_path: str) -> None:
        """Deserialize model weights and config from the artifact path."""
        pass

    @abstractmethod
    def get_metadata(self) -> ModelMetadata:
        """Return the metadata of the currently loaded model version."""
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """Returns True if the model is loaded and ready to serve predictions."""
        pass
