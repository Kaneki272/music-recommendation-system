"""
Popularity Model Demo
=====================
Demonstrates Phase 7 Popularity Baseline training and prediction.
"""
import asyncio
from datetime import datetime, timedelta
import yaml

from ml.popularity.config import PopularityConfig, PopularityMode
from ml.popularity.model import PopularityModel
from ml.contracts.interactions import InteractionDataset, InteractionRecord, InteractionType
from ml.contracts.identifiers import UserId, SongId
from ml.contracts.recommendations import RecommendationRequest

def generate_mock_data() -> InteractionDataset:
    now = datetime(2026, 8, 14, 12, 0, 0)
    interactions = []
    
    # Song A: 10 plays today (Trending heavily)
    for i in range(10):
        interactions.append(InteractionRecord(
            user_id=UserId(f"user_{i}"),
            song_id=SongId("song_A_trending"),
            interaction_type=InteractionType.PLAY,
            timestamp=now - timedelta(hours=i),
            weight=1.0
        ))
        
    # Song B: 20 plays, but 2 years ago (Global classic)
    for i in range(20):
        interactions.append(InteractionRecord(
            user_id=UserId(f"user_{i}"),
            song_id=SongId("song_B_classic"),
            interaction_type=InteractionType.PLAY,
            timestamp=now - timedelta(days=700) + timedelta(hours=i),
            weight=1.0
        ))
        
    # Song C: 5 likes today (High weight, but fewer interactions)
    for i in range(5):
        interactions.append(InteractionRecord(
            user_id=UserId(f"user_{i}"),
            song_id=SongId("song_C_liked"),
            interaction_type=InteractionType.LIKE,
            timestamp=now - timedelta(hours=i),
            weight=4.0
        ))
        
    return InteractionDataset(
        dataset_version="mock_v1",
        date_range_start=now - timedelta(days=800),
        date_range_end=now,
        interactions=interactions,
        weight_config_version="v1"
    )

async def run_demo():
    print("\n" + "="*70)
    print("  PHASE 7 POPULARITY MODEL DEMO")
    print("="*70)
    
    dataset = generate_mock_data()
    print(f"\n[1] Mock Dataset Created: {len(dataset.interactions)} total interactions")
    
    # ---------------------------------------------------------
    # Scenario 1: GLOBAL Popularity (Massive half-life)
    # ---------------------------------------------------------
    print("\n" + "-"*70)
    print("  SCENARIO 1: GLOBAL POPULARITY (half_life_days=3650)")
    print("-"*70)
    global_config = PopularityConfig(mode=PopularityMode.GLOBAL, half_life_days=3650.0)
    global_model = PopularityModel(global_config)
    
    await global_model.train(dataset, reference_time=dataset.date_range_end)
    
    req = RecommendationRequest(user_id=UserId("test_user"), limit=5)
    res_global = await global_model.predict(req)
    
    for rec in res_global.recommendations:
        raw_score = global_model.scores.get(rec.song_id, 0.0)
        print(f"  Rank {rec.rank}: {rec.song_id:<20} | Raw Score: {raw_score:>5.1f} | Normalized: {rec.score:.4f}")
        
    print("  => Notice how 'song_B_classic' competes well because the long half-life preserves its 20 historical plays.")
    print("  => 'song_C_liked' also scores highly due to high-weight LIKE interactions (weight=4.0).")

    # ---------------------------------------------------------
    # Scenario 2: TRENDING Popularity (7-day Half-Life)
    # ---------------------------------------------------------
    print("\n" + "-"*70)
    print("  SCENARIO 2: TRENDING POPULARITY (half_life_days=7.0)")
    print("-"*70)
    trending_config = PopularityConfig(mode=PopularityMode.TRENDING, half_life_days=7.0)
    trending_model = PopularityModel(trending_config)
    
    await trending_model.train(dataset, reference_time=dataset.date_range_end)
    
    res_trending = await trending_model.predict(req)
    
    for rec in res_trending.recommendations:
        raw_score = trending_model.scores.get(rec.song_id, 0.0)
        print(f"  Rank {rec.rank}: {rec.song_id:<20} | Raw Score: {raw_score:>5.1f} | Normalized: {rec.score:.4f}")
        
    print("  => Notice how 'song_B_classic' score decays to 0.0 due to the 7-day half-life over 700 days.")
    print("  => 'song_C_liked' and 'song_A_trending' take over because they are recent.")
    
    # ---------------------------------------------------------
    # Scenario 3: Artifact Generation
    # ---------------------------------------------------------
    print("\n" + "-"*70)
    print("  SCENARIO 3: ARTIFACT SERIALIZATION")
    print("-"*70)
    
    import tempfile
    import os
    with tempfile.TemporaryDirectory() as tmpdir:
        await trending_model.save(tmpdir)
        print(f"  Saved model artifacts to a temporary directory")
        print("  Files generated:")
        for f in os.listdir(tmpdir):
            print(f"   - {f}")
            
        with open(os.path.join(tmpdir, "config.yaml")) as f:
            print("\n  config.yaml contents:")
            print("  " + "\n  ".join(f.read().splitlines()))
            
    print("\n" + "="*70)
    print("  DEMO COMPLETE")
    print("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(run_demo())
