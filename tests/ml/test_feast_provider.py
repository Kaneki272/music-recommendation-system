"""
Tests for Feast Feature Provider
================================
Mocks the Feast FeatureStore and QdrantVectorStore to verify 
the adapter logic in FeastFeatureProvider.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
import json

from feature_store.feast_provider import FeastFeatureProvider
from ml.contracts.identifiers import SongId, UserId, CANONICAL_VECTOR_DIMENSION

@pytest.fixture
def mock_feast_store():
    store = MagicMock()
    return store

@pytest.fixture
def mock_qdrant_store():
    store = AsyncMock()
    return store

@pytest.fixture
def feature_provider(mock_feast_store, mock_qdrant_store):
    provider = FeastFeatureProvider(repo_path="dummy/path", qdrant_store=mock_qdrant_store)
    provider.store = mock_feast_store  # override the actual store
    return provider

@pytest.mark.asyncio
async def test_get_audio_features(feature_provider, mock_qdrant_store):
    song_id = SongId("123e4567-e89b-12d3-a456-426614174000")
    valid_vector = [0.1] * CANONICAL_VECTOR_DIMENSION
    mock_qdrant_store.get.return_value = valid_vector
    
    result = await feature_provider.get_audio_features(song_id)
    
    assert result is not None
    assert result.song_id == song_id
    assert result.audio_feature_vector == valid_vector
    assert result.feature_dimension == CANONICAL_VECTOR_DIMENSION
    mock_qdrant_store.get.assert_called_once_with(song_id)

@pytest.mark.asyncio
async def test_get_user_representation_new_user(feature_provider, mock_feast_store):
    user_id = UserId("987e6543-e21b-12d3-a456-426614174000")
    
    # Mock Feast returning empty or None for listening_history_count
    mock_response = MagicMock()
    mock_response.to_dict.return_value = {
        "listening_history_count": [None],
        "recently_played_ids": [None],
        "favorite_genres": [None],
        "acoustic_preferences": [None]
    }
    mock_feast_store.get_online_features.return_value = mock_response
    
    result = await feature_provider.get_user_representation(user_id)
    
    assert result is not None
    assert result.user_id == user_id
    assert result.is_new_user is True
    assert result.listening_history_count == 0

@pytest.mark.asyncio
async def test_get_user_representation_existing_user(feature_provider, mock_feast_store):
    user_id = UserId("987e6543-e21b-12d3-a456-426614174000")
    
    mock_response = MagicMock()
    mock_response.to_dict.return_value = {
        "listening_history_count": [150],
        "recently_played_ids": [json.dumps(["song1", "song2"])],
        "favorite_genres": [json.dumps(["Rock", "Jazz"])],
        "acoustic_preferences": [json.dumps({"tempo_bpm_mean": 120.0})]
    }
    mock_feast_store.get_online_features.return_value = mock_response
    
    result = await feature_provider.get_user_representation(user_id)
    
    assert result is not None
    assert result.is_new_user is False
    assert result.listening_history_count == 150
    assert "Rock" in result.favorite_genres
    assert result.acoustic_preferences["tempo_bpm_mean"] == 120.0
