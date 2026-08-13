"""
Tests for Content-Based Filtering (Phase 8)
===========================================
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from ml.contracts.identifiers import SongId, UserId, CANONICAL_VECTOR_DIMENSION
from ml.contracts.interactions import InteractionRecord, InteractionType, InteractionDataset
from ml.contracts.audio import AudioFeatureVector
from ml.contracts.content import ContentRepresentation, MetadataFeatureVector
from ml.contracts.user import UserRepresentation
from ml.contracts.recommendations import RecommendationRequest
from ml.content_based.profiler import UserTasteProfiler
from ml.content_based.similarity import calculate_genre_similarity, calculate_metadata_boost
from ml.content_based.model import ContentBasedModel
from ml.interfaces.embedding_provider import VectorSearchResult

def test_profiler_time_decay():
    profiler = UserTasteProfiler(half_life_days=10.0)
    ref_time = datetime(2026, 8, 1)
    
    # Exactly 10 days old
    t1 = datetime(2026, 7, 22)
    decay = profiler._calculate_decay(t1, ref_time)
    assert decay == 0.5
    
    # Future interaction (leakage prevention)
    t2 = datetime(2026, 8, 2)
    decay2 = profiler._calculate_decay(t2, ref_time)
    assert decay2 == 0.0

def test_profiler_aggregation():
    profiler = UserTasteProfiler(half_life_days=10.0)
    ref_time = datetime(2026, 8, 1)
    
    i1 = InteractionRecord(user_id=UserId("u1"), song_id=SongId("s1"), interaction_type=InteractionType.PLAY, timestamp=datetime(2026, 7, 22), weight=1.0)
    a1 = AudioFeatureVector(song_id=SongId("s1"), audio_feature_vector=[1.0] * CANONICAL_VECTOR_DIMENSION, feature_dimension=CANONICAL_VECTOR_DIMENSION, extraction_version="v1", preprocessing_version="v1")
    
    profile_vector = profiler.generate_profile([i1], [a1], ref_time)
    assert profile_vector is not None
    assert len(profile_vector) == CANONICAL_VECTOR_DIMENSION
    assert profile_vector[0] == 1.0  # (1.0 * 0.5) / 0.5 = 1.0

def test_metadata_similarity():
    # Genre sim
    sim = calculate_genre_similarity(["Rock", "Pop"], ["Rock", "Jazz"])
    # intersection: Rock (1). candidate len: 2. sim: 1/2 = 0.5
    assert sim == 0.5
    
    # Boost
    meta = MetadataFeatureVector(song_id=SongId("s1"), duration_ms=1000, genres=["Rock", "Jazz"])
    boost = calculate_metadata_boost(["Rock"], [], meta, genre_weight=0.5, artist_weight=0.0)
    # intersection 1, cand len 2 -> 0.5 sim. weight 0.5 -> boost 0.25
    assert boost == 0.25

@pytest.mark.asyncio
async def test_content_based_model_predict():
    # Mocks
    mock_feature_provider = AsyncMock()
    mock_vector_store = AsyncMock()
    
    user_rep = UserRepresentation(user_id=UserId("u1"), listening_history_count=10, favorite_genres=["Rock"])
    mock_feature_provider.get_user_representation.return_value = user_rep
    
    a1 = AudioFeatureVector(song_id=SongId("s1"), audio_feature_vector=[1.0] * CANONICAL_VECTOR_DIMENSION, feature_dimension=CANONICAL_VECTOR_DIMENSION, extraction_version="v1", preprocessing_version="v1")
    mock_feature_provider.batch_get_audio_features.return_value = [a1]
    
    meta = MetadataFeatureVector(song_id=SongId("s2"), duration_ms=1000, genres=["Rock"])
    content_rep = ContentRepresentation(song_id=SongId("s2"), metadata_features=meta)
    mock_feature_provider.get_content_representation.return_value = content_rep
    
    # Qdrant returns candidate s2
    mock_vector_store.search.return_value = [VectorSearchResult(song_id=SongId("s2"), score=0.8)]
    
    model = ContentBasedModel(mock_feature_provider, mock_vector_store)
    
    dataset = InteractionDataset(
        dataset_version="v1", date_range_start=datetime(2026,1,1), date_range_end=datetime(2026,8,1),
        interactions=[InteractionRecord(user_id=UserId("u1"), song_id=SongId("s1"), interaction_type=InteractionType.PLAY, timestamp=datetime(2026,7,1), weight=1.0)],
        weight_config_version="v1"
    )
    
    await model.train(dataset)
    
    req = RecommendationRequest(user_id=UserId("u1"), limit=5)
    res = await model.predict(req)
    
    assert len(res.recommendations) == 1
    assert res.recommendations[0].song_id == "s2"
    # Audio score (0.8 * 1.0) + Genre Boost (1/1 * 0.5) = 1.3
    assert res.recommendations[0].score == 1.3
