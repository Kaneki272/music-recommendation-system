"""
ML Interface — Feature Provider
==================================
Models should not directly query PostgreSQL or MongoDB.
They consume features through this interface.

This decouples model code from database implementation details.
In production, the implementation may read from a Redis feature cache,
a Feast feature store, or directly from the database.
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from ml.contracts.audio import AudioFeatureVector
from ml.contracts.content import ContentRepresentation
from ml.contracts.user import UserRepresentation
from ml.contracts.identifiers import SongId, UserId


class FeatureProviderInterface(ABC):
    """Abstract source for pre-computed features consumed by ML models."""

    @abstractmethod
    async def get_audio_features(self, song_id: SongId) -> Optional[AudioFeatureVector]:
        """Retrieve the 222-dim audio_feature_vector for a song."""
        pass

    @abstractmethod
    async def get_content_representation(self, song_id: SongId) -> Optional[ContentRepresentation]:
        """Retrieve the full multi-modal content representation for a song."""
        pass

    @abstractmethod
    async def get_user_representation(self, user_id: UserId) -> Optional[UserRepresentation]:
        """Retrieve the current user representation including behavioral history."""
        pass

    @abstractmethod
    async def batch_get_audio_features(self, song_ids: List[SongId]) -> List[AudioFeatureVector]:
        """Retrieve audio features for multiple songs efficiently."""
        pass
