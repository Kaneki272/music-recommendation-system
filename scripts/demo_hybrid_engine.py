import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import asyncio
from typing import List, Dict
from datetime import datetime

from ml.contracts.recommendations import RecommendationRequest
from ml.hybrid.engine import HybridRecommendationEngine
from ml.hybrid.config import HybridConfig

class MockPopularityModel:
    def __init__(self):
        self.scores = {
            "Adele - Hello.mp3": 9500.0,
            "Alan Walker - Faded.mp3": 8800.0,
            "Imagine Dragons - Believer.mp3": 8200.0,
            "Ed Sheeran - Shape of You.mp3": 7900.0,
            "synth_upbeat.wav": 3000.0,
        }

class MockALSModel:
    def recommend_top_k(self, user_id: str, k: int, exclude_song_ids=None):
        # Collaborative filtering returns personalized user interaction preferences
        scores = [
            ("Adele - Hello.mp3", 1.85),
            ("Ed Sheeran - Shape of You.mp3", 1.42),
            ("Alan Walker - Faded.mp3", 1.10),
            ("synth_ballad.wav", 0.95),
        ]
        return scores, None

class MockContentBasedModel:
    def recommend_top_k(self, user_id: str, k: int, exclude_song_ids=None):
        # Audio feature similarity model (Librosa DSP vectors)
        scores = [
            ("Adele - Someone Like You.mp3", 0.98),
            ("Adele - Hello.mp3", 0.95),
            ("synth_ambient.wav", 0.91),
            ("Alan Walker - Faded.mp3", 0.88),
        ]
        return scores, None

async def run_hybrid_demo():
    print("=" * 72)
    print("  HYBRID RECOMMENDATION ENGINE DEMO")
    print("  Fusing Collaborative Filtering (ALS) + Content-Based Audio + Popularity")
    print("=" * 72)

    als_model = MockALSModel()
    pop_model = MockPopularityModel()
    content_model = MockContentBasedModel()

    # User interaction counts to simulate NEW_USER vs SPARSE_USER vs KNOWN_USER
    user_counts = {
        "user_new": 0,       # Cold-start new user
        "user_sparse": 3,    # Low history user
        "user_known": 45,    # Active experienced user
    }

    engine = HybridRecommendationEngine(
        als_model=als_model,
        popularity_model=pop_model,
        content_model=content_model,
        user_interaction_counts=user_counts,
        als_min=-0.5,
        als_max=2.0,
        max_pop=10000.0,
        content_available=True
    )

    for user_id, count in user_counts.items():
        state = engine.get_user_state(user_id)
        req = RecommendationRequest(
            user_id=user_id,
            limit=4,
            exclude_song_ids=[]
        )
        response = await engine.predict(req)

        print(f"\n----------------------------------------------------------------------")
        print(f" USER: {user_id:<12} | Interactions: {count:>2} | User State: {state}")
        print(f" Active Fusion Weights: {response.metadata['active_weights']}")
        print(f"----------------------------------------------------------------------")

        for rank, rec in enumerate(response.recommendations, 1):
            contrib = rec.metadata.get("contributions", {})
            als_c = contrib.get("als", 0.0)
            pop_c = contrib.get("popularity", 0.0)
            cnt_c = contrib.get("content", 0.0)

            print(f"  Rank {rank}: {rec.song_id:<32} | Final Score: {rec.score:.4f}")
            print(f"          Score Breakdown -> [ALS: {als_c:.4f} | Content: {cnt_c:.4f} | Pop: {pop_c:.4f}]")

if __name__ == "__main__":
    asyncio.run(run_hybrid_demo())
