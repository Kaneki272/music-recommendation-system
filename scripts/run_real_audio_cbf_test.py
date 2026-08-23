import os
import sys
import json
import asyncio
from datetime import datetime, timezone
import numpy as np

# Database and Qdrant
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models.song import Song
from backend.database.qdrant.client import QdrantVectorStore

# Interfaces and contracts
from ml.interfaces.feature_provider import FeatureProviderInterface
from ml.contracts.audio import AudioFeatureVector
from ml.contracts.content import ContentRepresentation
from ml.contracts.user import UserRepresentation
from ml.contracts.identifiers import SongId, UserId
from ml.contracts.recommendations import RecommendationRequest
from ml.contracts.interactions import InteractionDataset, InteractionRecord, InteractionType

# Model components
from ml.content_based.model import ContentBasedModel
from ml.content_based.config import ContentBasedConfig

DB_URL = os.environ.get("POSTGRES_URI", "sqlite:///recsys.db")

class LocalFeatureProvider(FeatureProviderInterface):
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
        # Mock metadata features (empty for now, so no metadata boost applies)
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

async def main():
    print("Initializing components...")
    engine = create_engine(DB_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    songs = db.query(Song).all()
    song_map = {str(s.id): s.title for s in songs}
    title_map = {s.title: str(s.id) for s in songs}
    
    qstore = QdrantVectorStore(collection_name="audio_v2", path="datasets/processed/qdrant_db")
    
    out = []
    def p(text):
        out.append(text)
        print(text)

    p("# Real Audio Content-Based Recommendation Test")
    p("\n## Test A: Song-to-Song Similarity")
    
    # Test A: Direct Qdrant retrieval (Diagnostic)
    for sid_str, title in song_map.items():
        sid = SongId(sid_str)
        vec = await qstore.get(sid)
        if not vec:
            continue
        p(f"\n**Source Song:** `{title}` (ID: {sid_str})")
        # Query top 4 to remove source
        hits = await qstore.search(query_vector=vec, top_k=4)
        
        # Remove source song itself
        cands = [h for h in hits if str(h.song_id) != sid_str][:3]
        
        for rank, cand in enumerate(cands, 1):
            cand_title = song_map.get(str(cand.song_id), "Unknown")
            p(f"- Rank {rank}: `{cand_title}` (Score: {cand.score:.4f})")
            
            # Validation
            if str(cand.song_id) == sid_str:
                raise ValueError("Source song was not excluded!")
            if not np.isfinite(cand.score):
                raise ValueError("Score is not finite!")

    # Setup for Test B, C, D using the Model Architecture
    p("\n## Test B: User Taste Profile Recommendation")
    
    u_test_id = UserId("U_TEST_001")
    ref_time = datetime.now(timezone.utc)
    
    s1 = title_map.get("soundhelix_song1.mp3")
    s2 = title_map.get("soundhelix_song2.mp3")
    s3 = title_map.get("soundhelix_song3.mp3")
    
    if not (s1 and s2 and s3):
        p("Missing required test songs in DB. Cannot proceed with Test B.")
        return
        
    from datetime import timedelta
    interact_time = ref_time - timedelta(days=1)
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
    
    fp = LocalFeatureProvider(qstore=qstore, is_cold_start=False)
    config = ContentBasedConfig()
    model = ContentBasedModel(feature_provider=fp, vector_store=qstore, config=config)
    await model.train(dataset, reference_time=ref_time)
    
    req_b = RecommendationRequest(user_id=u_test_id, limit=3, exclude_song_ids=[])
    res_b = await model.predict(req_b)
    
    p(f"\nUser `U_TEST_001` interacting with `{song_map[s1]}` (LIKE), `{song_map[s2]}` (PLAY), `{song_map[s3]}` (COMPLETE)")
    p(f"Profile State: `{res_b.metadata.get('profile_state')}`")
    
    for rec in res_b.recommendations:
        title = song_map.get(str(rec.song_id), "Unknown")
        p(f"- Rank {rec.rank}: `{title}` (Score: {rec.score:.4f})")
        
    # Test C: Exclusion Behavior
    p("\n## Test C: Exclusion Test")
    exclude_sid = res_b.recommendations[0].song_id
    exclude_title = song_map.get(str(exclude_sid))
    p(f"\nExcluding the top recommendation: `{exclude_title}`")
    
    req_c = RecommendationRequest(user_id=u_test_id, limit=3, exclude_song_ids=[exclude_sid])
    res_c = await model.predict(req_c)
    
    found_excluded = False
    for rec in res_c.recommendations:
        title = song_map.get(str(rec.song_id), "Unknown")
        p(f"- Rank {rec.rank}: `{title}` (Score: {rec.score:.4f})")
        if rec.song_id == exclude_sid:
            found_excluded = True
            
    if found_excluded:
        raise ValueError(f"Explicitly excluded song {exclude_sid} was recommended!")
    else:
        p("\n[PASS] Exclusion successful: Explicitly excluded song was not recommended.")
        
    # Test D: Cold Start Behavior
    p("\n## Test D: Cold-Start Behavior")
    u_cold_id = UserId("U_COLD_001")
    
    fp_cold = LocalFeatureProvider(qstore=qstore, is_cold_start=True)
    model_cold = ContentBasedModel(feature_provider=fp_cold, vector_store=qstore, config=config)
    await model_cold.train(dataset, reference_time=ref_time)
    
    req_d = RecommendationRequest(user_id=u_cold_id, limit=3)
    res_d = await model_cold.predict(req_d)
    
    p(f"\nUser `U_COLD_001` with NO history.")
    p(f"Profile State: `{res_d.metadata.get('profile_state')}`")
    p(f"Recommendations returned: {len(res_d.recommendations)}")
    
    if len(res_d.recommendations) > 0:
        raise ValueError("Cold start user returned fabricated recommendations!")
    else:
        p("[PASS] Cold-start successful: No fabricated recommendations returned.")

    os.makedirs("docs", exist_ok=True)
    with open("docs/ContentBasedRealAudioTest.md", "w") as f:
        f.write("\n".join(out))
        
if __name__ == "__main__":
    asyncio.run(main())
