import pandas as pd
import sys
import os
import asyncio

# Ensure paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from ml.popularity.scoring import PopularityModel
from ml.collaborative.model import CollaborativeFilteringModel
from ml.hybrid.engine import HybridRecommendationEngine
from ml.collaborative.evaluator import Evaluator
from ml.contracts.recommendations import RecommendationRequest

def mock_predict(user_id, candidates, hybrid_engine):
    req = RecommendationRequest(
        user_id=user_id,
        limit=50,
        exclude_song_ids=[]
    )
    # This is a bit of a hack since predict is async, 
    # but evaluator expects a sync predict/recommend_top_k
    # We will wrap HybridEngine to provide sync recommend_top_k
    pass

class SyncHybridWrapper:
    def __init__(self, engine, train_users):
        self.engine = engine
        self.train_users = train_users

    def recommend_top_k(self, user_id, k, exclude_song_ids=None):
        exclude = exclude_song_ids or []
        req = RecommendationRequest(
            user_id=user_id,
            limit=k,
            exclude_song_ids=exclude
        )
        
        # Run async predict synchronously
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
        
        response = loop.run_until_complete(self.engine.predict(req))
        recs = [(r.song_id, r.score) for r in response.recommendations]
        return recs, None

def main():
    print("Loading datasets...")
    train_df = pd.read_parquet("datasets/intermediate/train.parquet")
    val_df = pd.read_parquet("datasets/intermediate/validation.parquet")

    user_counts = train_df.groupby('user_id').size().to_dict()
    train_users = train_df.groupby('user_id')['song_id'].apply(set).to_dict()

    print("Initializing Popularity Model...")
    pop_model = PopularityModel()
    # It expects dataset_version, but we can just use load() or train()
    # Let's train it manually for quickness or use proper train
    pop_model.train_sync(train_df)

    print("Initializing ALS Model...")
    als_model = CollaborativeFilteringModel()
    # Train using the frozen config
    als_model.train(
        train_df=train_df,
        factors=32,
        regularization=0.01,
        alpha=1.0,
        iterations=15
    )
    
    # We need normalizer boundaries. Pop max:
    max_pop = float(max(pop_model.pop_counts.values()))
    print(f"Max popularity: {max_pop}")
    
    evaluator = Evaluator(k_values=[5, 10])

    configs = {
        "A: Pop Only": {"als": 0.0, "popularity": 1.0, "content": 0.0},
        "B: ALS Only": {"als": 1.0, "popularity": 0.0, "content": 0.0},
        "C: ALS 0.9 / Pop 0.1": {"als": 0.90, "popularity": 0.10, "content": 0.0},
        "D: ALS 0.8 / Pop 0.2": {"als": 0.80, "popularity": 0.20, "content": 0.0},
        "E: ALS 0.7 / Pop 0.3": {"als": 0.70, "popularity": 0.30, "content": 0.0},
        "F: ALS 0.6 / Pop 0.4": {"als": 0.60, "popularity": 0.40, "content": 0.0},
        "G: ALS 0.5 / Pop 0.5": {"als": 0.50, "popularity": 0.50, "content": 0.0},
    }

    results = {}
    
    for name, weights in configs.items():
        print(f"\nEvaluating configuration: {name} -> {weights}")
        
        # Override HybridConfig weights temporarily via monkeypatch for the test
        from ml.hybrid.config import HybridConfig
        HybridConfig.WEIGHTS_KNOWN_USER = weights
        HybridConfig.WEIGHTS_SPARSE_USER = weights
        HybridConfig.WEIGHTS_NEW_USER = weights

        engine = HybridRecommendationEngine(
            als_model=als_model,
            popularity_model=pop_model,
            content_model=None,
            user_interaction_counts=user_counts,
            song_to_artist_map={},
            als_min=0.0, als_max=1.0, # implicit ALS returns dot products which we can scale, or just rely on raw normalization
            max_pop=max_pop,
            content_available=False
        )
        
        wrapper = SyncHybridWrapper(engine, train_users)
        metrics = evaluator.evaluate(wrapper, train_df, val_df)
        
        results[name] = metrics
        
        print(f"  NDCG@10: {metrics['NDCG@10']:.4f}")
        print(f"  HitRate@10: {metrics['HitRate@10']:.4f}")

    print("\n--- Summary ---")
    for name, m in results.items():
        print(f"{name:25s} | NDCG@10: {m['NDCG@10']:.4f} | HR@10: {m['HitRate@10']:.4f}")

if __name__ == "__main__":
    main()
