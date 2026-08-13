"""
Feast Feature Provider
======================
Implements FeatureProviderInterface using Feast for structured features
and Qdrant for Audio features.

Models call this provider, which abstracts away whether features are
coming from Redis (online) or Qdrant (dense vectors).
"""
import json
from typing import List, Optional
from feast import FeatureStore
import os

from ml.interfaces.feature_provider import FeatureProviderInterface
from ml.interfaces.embedding_provider import VectorStoreInterface
from ml.contracts.audio import AudioFeatureVector
from ml.contracts.content import ContentRepresentation, MetadataFeatureVector
from ml.contracts.user import UserRepresentation
from ml.contracts.identifiers import SongId, UserId

class FeastFeatureProvider(FeatureProviderInterface):
    """
    Integrates Feast (for structured metadata/behavior) 
    and Qdrant (for dense audio features).
    """
    def __init__(self, repo_path: str, qdrant_store: VectorStoreInterface):
        # In a real setup, repo_path points to the Feast repository directory
        self.store = FeatureStore(repo_path=repo_path)
        self.qdrant = qdrant_store

    async def get_audio_features(self, song_id: SongId) -> Optional[AudioFeatureVector]:
        # Audio features are stored as vectors in Qdrant + payload
        # Wait! VectorStoreInterface only has `get` returning vector. 
        # But we need payload too for `extraction_version`. Let's use `search` 
        # or expand `get` if needed, but for now we can rely on Qdrant's payload.
        # Let's assume VectorStoreInterface has a way or we just fetch vector.
        vector = await self.qdrant.get(song_id)
        if not vector:
            return None
        
        # In practice, we would fetch extraction_version from the Qdrant payload or Feast.
        return AudioFeatureVector(
            song_id=song_id,
            audio_feature_vector=vector,
            feature_dimension=len(vector),
            extraction_version="v1.0.0", # Simplified
            preprocessing_version="v1.0.0"
        )

    async def get_content_representation(self, song_id: SongId) -> Optional[ContentRepresentation]:
        # 1. Fetch metadata from Feast (Online Store / Redis)
        feature_vector = self.store.get_online_features(
            features=[
                "song_metadata:duration_ms",
                "song_metadata:explicit",
                "song_metadata:release_year",
                "song_metadata:genres",
                "song_metadata:artist_popularity"
            ],
            entity_rows=[{"song_id": song_id}]
        ).to_dict()

        metadata_features = None
        # Check if duration_ms exists and is not None to confirm entity was found
        if feature_vector.get("duration_ms") and feature_vector["duration_ms"][0] is not None:
            # Parse genres from string
            genres_raw = feature_vector["genres"][0]
            genres_list = json.loads(genres_raw) if genres_raw else []
            
            metadata_features = MetadataFeatureVector(
                song_id=song_id,
                duration_ms=int(feature_vector["duration_ms"][0]),
                explicit=bool(feature_vector["explicit"][0]),
                release_year=int(feature_vector["release_year"][0]) if feature_vector["release_year"][0] else None,
                genres=genres_list,
                artist_popularity=float(feature_vector["artist_popularity"][0]) if feature_vector["artist_popularity"][0] else None
            )

        # 2. Fetch audio vector from Qdrant
        audio_features = await self.get_audio_features(song_id)
        
        if not metadata_features and not audio_features:
            return None

        return ContentRepresentation(
            song_id=song_id,
            audio_features=audio_features,
            metadata_features=metadata_features
        )

    async def get_user_representation(self, user_id: UserId) -> Optional[UserRepresentation]:
        # Fetch user behavior from Feast
        feature_vector = self.store.get_online_features(
            features=[
                "user_behavior:listening_history_count",
                "user_behavior:recently_played_ids",
                "user_behavior:favorite_genres",
                "user_behavior:acoustic_preferences"
            ],
            entity_rows=[{"user_id": user_id}]
        ).to_dict()

        if not feature_vector.get("listening_history_count") or feature_vector["listening_history_count"][0] is None:
            # New user (cold start fallback logic)
            return UserRepresentation(
                user_id=user_id,
                listening_history_count=0
            )
            
        def parse_json(val):
            return json.loads(val) if val else []

        return UserRepresentation(
            user_id=user_id,
            listening_history_count=int(feature_vector["listening_history_count"][0]),
            recently_played=parse_json(feature_vector["recently_played_ids"][0]),
            favorite_genres=parse_json(feature_vector["favorite_genres"][0]),
            acoustic_preferences=json.loads(feature_vector["acoustic_preferences"][0]) if feature_vector["acoustic_preferences"][0] else {}
        )

    async def batch_get_audio_features(self, song_ids: List[SongId]) -> List[AudioFeatureVector]:
        # A true batch implementation would fetch all from Qdrant in one request.
        # Simplified for now.
        results = []
        for sid in song_ids:
            feat = await self.get_audio_features(sid)
            if feat:
                results.append(feat)
        return results
