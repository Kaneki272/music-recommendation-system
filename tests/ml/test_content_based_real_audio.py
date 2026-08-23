import os
import pytest
from datetime import datetime, timezone, timedelta
import numpy as np
import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models.song import Song
from backend.database.qdrant.client import QdrantVectorStore

from ml.interfaces.feature_provider import FeatureProviderInterface
from ml.contracts.audio import AudioFeatureVector
from ml.contracts.content import ContentRepresentation
from ml.contracts.user import UserRepresentation
from ml.contracts.identifiers import SongId, UserId
from ml.contracts.recommendations import RecommendationRequest
from ml.contracts.interactions import InteractionDataset, InteractionRecord, InteractionType

from ml.content_based.model import ContentBasedModel
from ml.content_based.config import ContentBasedConfig

DB_URL = os.environ.get("POSTGRES_URI", "sqlite:///recsys.db")


class LocalTestFeatureProvider(FeatureProviderInterface):
    def __init__(self, qstore, is_cold_start=False):
        self.qstore = qstore
        self.is_cold_start = is_cold_start

    async def get_audio_features(self, song_id: SongId) -> AudioFeatureVector:
        vec = await self.qstore.get(song_id)
        if vec is None:
            return None
        return AudioFeatureVector(
            song_id=song_id,
            audio_feature_vector=vec,
            feature_dimension=len(vec),
            extraction_version="audio_v2",
            preprocessing_version="audio_v1"
        )

    async def get_content_representation(self, song_id: SongId) -> ContentRepresentation:
        return ContentRepresentation(song_id=song_id, metadata_features=None)

    async def get_user_representation(self, user_id: UserId) -> UserRepresentation:
        if self.is_cold_start:
            return UserRepresentation(user_id=user_id, listening_history_count=0)
        return UserRepresentation(user_id=user_id, listening_history_count=10)

    async def batch_get_audio_features(self, song_ids: list[SongId]) -> list[AudioFeatureVector]:
        feats = []
        for sid in song_ids:
            v = await self.get_audio_features(sid)
            if v:
                feats.append(v)
        return feats


@pytest.fixture(scope="module")
def real_audio_qstore():
    # Only run tests if qdrant DB exists locally
    path = "datasets/processed/qdrant_db"
    if not os.path.exists(path):
        pytest.skip("Real audio Qdrant database not found. Run ingestion first.")
    return QdrantVectorStore(collection_name="audio_v2", path=path)

@pytest.fixture(scope="module")
def real_audio_songs():
    if not os.path.exists("recsys.db"):
        pytest.skip("recsys.db not found. Run ingestion first.")
    
    engine = create_engine(DB_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    songs = db.query(Song).all()
    db.close()
    
    if len(songs) == 0:
        pytest.skip("No songs in recsys.db.")
    return songs


@pytest.mark.asyncio
async def test_song_to_song_retrieval(real_audio_qstore, real_audio_songs):
    # Test A: Song-to-Song
    for song in real_audio_songs:
        sid_str = str(song.id)
        sid = SongId(sid_str)
        vec = await real_audio_qstore.get(sid)
        if not vec:
            continue
            
        hits = await real_audio_qstore.search(query_vector=vec, top_k=4)
        cands = [h for h in hits if str(h.song_id) != sid_str][:3]
        
        assert len(cands) > 0, "No similar songs found."
        
        # Constraints validation
        for cand in cands:
            assert str(cand.song_id) != sid_str, "Source song was not excluded!"
            assert np.isfinite(cand.score), "Score is not finite!"
            assert not np.isnan(cand.score), "Score is NaN!"


@pytest.mark.asyncio
async def test_user_profile_recommendation(real_audio_qstore, real_audio_songs):
    if len(real_audio_songs) < 3:
        pytest.skip("Need at least 3 songs for profile testing.")
        
    s1, s2, s3 = [str(s.id) for s in real_audio_songs[:3]]
    
    ref_time = datetime.now(timezone.utc)
    interact_time = ref_time - timedelta(days=1)
    u_test_id = UserId("U_TEST_001")
    
    interactions = [
        InteractionRecord(user_id=u_test_id, song_id=SongId(s1), interaction_type=InteractionType.LIKE, timestamp=interact_time, weight=4.0),
        InteractionRecord(user_id=u_test_id, song_id=SongId(s2), interaction_type=InteractionType.PLAY, timestamp=interact_time, weight=1.0),
        InteractionRecord(user_id=u_test_id, song_id=SongId(s3), interaction_type=InteractionType.COMPLETE, timestamp=interact_time, weight=2.0)
    ]
    
    dataset = InteractionDataset(
        dataset_version="test",
        date_range_start=interact_time,
        date_range_end=ref_time,
        interactions=interactions,
        weight_config_version="v1"
    )
    
    fp = LocalTestFeatureProvider(qstore=real_audio_qstore, is_cold_start=False)
    config = ContentBasedConfig()
    model = ContentBasedModel(feature_provider=fp, vector_store=real_audio_qstore, config=config)
    await model.train(dataset, reference_time=ref_time)
    
    req = RecommendationRequest(user_id=u_test_id, limit=3)
    res = await model.predict(req)
    
    assert res.metadata["profile_state"] == "NORMAL", "Profile state should be NORMAL with 3 valid interactions."
    assert len(res.recommendations) > 0, "No recommendations returned."
    
    # Check ordering
    scores = [r.score for r in res.recommendations]
    assert scores == sorted(scores, reverse=True), "Scores are not in descending order."


@pytest.mark.asyncio
async def test_exclusion_filtering(real_audio_qstore, real_audio_songs):
    if len(real_audio_songs) < 3:
        pytest.skip("Need at least 3 songs for testing.")
        
    s1 = str(real_audio_songs[0].id)
    
    ref_time = datetime.now(timezone.utc)
    interact_time = ref_time - timedelta(days=1)
    u_test_id = UserId("U_EXCLUDE_001")
    
    interactions = [
        InteractionRecord(user_id=u_test_id, song_id=SongId(s1), interaction_type=InteractionType.LIKE, timestamp=interact_time, weight=4.0),
    ]
    
    dataset = InteractionDataset(
        dataset_version="test",
        date_range_start=interact_time,
        date_range_end=ref_time,
        interactions=interactions,
        weight_config_version="v1"
    )
    
    fp = LocalTestFeatureProvider(qstore=real_audio_qstore, is_cold_start=False)
    config = ContentBasedConfig(minimum_interaction_threshold=1)
    model = ContentBasedModel(feature_provider=fp, vector_store=real_audio_qstore, config=config)
    await model.train(dataset, reference_time=ref_time)
    
    # Run once without exclusion to find top recommendation
    req_unfiltered = RecommendationRequest(user_id=u_test_id, limit=3)
    res_unfiltered = await model.predict(req_unfiltered)
    
    if not res_unfiltered.recommendations:
        pytest.skip("No recommendations found.")
        
    exclude_sid = res_unfiltered.recommendations[0].song_id
    
    # Run again with exclusion
    req_filtered = RecommendationRequest(user_id=u_test_id, limit=3, exclude_song_ids=[exclude_sid])
    res_filtered = await model.predict(req_filtered)
    
    for r in res_filtered.recommendations:
        assert r.song_id != exclude_sid, f"Explicitly excluded song {exclude_sid} was recommended!"


@pytest.mark.asyncio
async def test_cold_start_behavior(real_audio_qstore):
    ref_time = datetime.now(timezone.utc)
    u_cold_id = UserId("U_COLD_001")
    
    dataset = InteractionDataset(
        dataset_version="test",
        date_range_start=ref_time,
        date_range_end=ref_time,
        interactions=[],
        weight_config_version="v1"
    )
    
    fp = LocalTestFeatureProvider(qstore=real_audio_qstore, is_cold_start=True)
    config = ContentBasedConfig()
    model = ContentBasedModel(feature_provider=fp, vector_store=real_audio_qstore, config=config)
    await model.train(dataset, reference_time=ref_time)
    
    req = RecommendationRequest(user_id=u_cold_id, limit=3)
    res = await model.predict(req)
    
    assert res.metadata["profile_state"] == "COLD_START", "Cold start should result in COLD_START profile state."
    assert len(res.recommendations) == 0, "Cold start should not return fabricated recommendations."
