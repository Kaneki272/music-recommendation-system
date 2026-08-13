"""
Tests for Popularity Recommendation Baseline
==========================================
"""
import pytest
from datetime import datetime, timedelta
import os
import shutil

from ml.contracts.identifiers import SongId, UserId
from ml.contracts.interactions import InteractionRecord, InteractionType, InteractionDataset
from ml.contracts.recommendations import RecommendationRequest
from ml.popularity.config import PopularityConfig, PopularityMode
from ml.popularity.scoring import calculate_decayed_weight
from ml.popularity.model import PopularityModel

@pytest.fixture
def mock_dataset():
    now = datetime.utcnow()
    # User 1 interactions
    i1 = InteractionRecord(
        user_id=UserId("u1"), song_id=SongId("s1"), 
        interaction_type=InteractionType.PLAY, timestamp=now - timedelta(days=10), weight=1.0
    )
    # User 2 interactions - Recent interaction for s2
    i2 = InteractionRecord(
        user_id=UserId("u2"), song_id=SongId("s2"), 
        interaction_type=InteractionType.LIKE, timestamp=now - timedelta(days=1), weight=4.0
    )
    # Old interaction for s2
    i3 = InteractionRecord(
        user_id=UserId("u3"), song_id=SongId("s2"), 
        interaction_type=InteractionType.PLAY, timestamp=now - timedelta(days=200), weight=1.0
    )
    
    return InteractionDataset(
        dataset_version="v1",
        date_range_start=now - timedelta(days=300),
        date_range_end=now,
        interactions=[i1, i2, i3],
        weight_config_version="v1"
    )

def test_exponential_decay():
    ref_time = datetime(2026, 8, 1)
    
    # Half-life 10 days, interaction exactly 10 days ago
    i1 = InteractionRecord(
        user_id=UserId("u1"), song_id=SongId("s1"), 
        interaction_type=InteractionType.PLAY, timestamp=datetime(2026, 7, 22), weight=10.0
    )
    
    weight = calculate_decayed_weight(i1, ref_time, half_life_days=10.0)
    assert weight == 5.0  # Decayed by exactly half

def test_future_leakage_returns_zero():
    ref_time = datetime(2026, 8, 1)
    # Interaction happens AFTER reference time
    i1 = InteractionRecord(
        user_id=UserId("u1"), song_id=SongId("s1"), 
        interaction_type=InteractionType.PLAY, timestamp=datetime(2026, 8, 2), weight=10.0
    )
    weight = calculate_decayed_weight(i1, ref_time, half_life_days=10.0)
    assert weight == 0.0

@pytest.mark.asyncio
async def test_popularity_model_training(mock_dataset):
    config = PopularityConfig(mode=PopularityMode.GLOBAL, half_life_days=180.0)
    model = PopularityModel(config=config)
    
    meta = await model.train(mock_dataset)
    assert meta.model_type == "popularity"
    assert model.is_ready() is True
    
    # s2 should have higher score than s1 due to the LIKE weight and recency
    assert model.scores["s2"] > model.scores["s1"]

@pytest.mark.asyncio
async def test_popularity_model_predict_exclusions(mock_dataset):
    model = PopularityModel()
    await model.train(mock_dataset)
    
    req = RecommendationRequest(
        user_id=UserId("u99"),
        limit=5,
        exclude_song_ids=[SongId("s2")]
    )
    
    res = await model.predict(req)
    assert len(res.recommendations) == 1
    assert res.recommendations[0].song_id == "s1"
    
    # Normalizer test - s1 should be 0.0 because it was the only one left?
    # Wait, normalizer was fit on ALL raw scores during train.
    # Min was s1's score, Max was s2's score. So s1 should be 0.0.
    assert res.recommendations[0].score == 0.0

@pytest.mark.asyncio
async def test_model_save_load(mock_dataset):
    model = PopularityModel()
    await model.train(mock_dataset, model_version="vtest")
    
    artifact_path = "models/popularity/vtest"
    await model.save(artifact_path)
    
    assert os.path.exists(os.path.join(artifact_path, "scores.json"))
    assert os.path.exists(os.path.join(artifact_path, "config.yaml"))
    assert os.path.exists(os.path.join(artifact_path, "metadata.json"))
    
    # Load into a new instance
    new_model = PopularityModel()
    await new_model.load(artifact_path)
    
    assert new_model.is_ready() is True
    assert new_model.scores == model.scores
    assert new_model.config.half_life_days == model.config.half_life_days
    
    shutil.rmtree(artifact_path)
