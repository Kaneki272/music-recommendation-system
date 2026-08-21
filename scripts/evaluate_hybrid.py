import pandas as pd
import numpy as np
import random
import os
import asyncio

from ml.collaborative.config import InteractionWeightsConfig, ALSConfig
from ml.collaborative.dataset_builder import DatasetBuilder
from ml.collaborative.model import CollaborativeFilteringModel
from ml.collaborative.candidate_generator import CandidateGenerator
from ml.collaborative.evaluator import Evaluator

from ml.hybrid.engine import HybridRecommendationEngine
from ml.hybrid.config import HybridConfig
from ml.contracts.recommendations import RecommendationRequest

class PopularityModelFast:
    """Wrapper to mimic the Popularity model interface for the hybrid engine in tests."""
    def __init__(self, train_df):
        self.pop_counts = train_df.groupby('song_id').size().sort_values(ascending=False)
        self.pop = self.pop_counts.index.tolist()
        self.scores = self.pop_counts.to_dict()
        
    def recommend_top_k(self, user_id, k, exclude_song_ids=None):
        exclude = set(exclude_song_ids or [])
        res = []
        for s in self.pop:
            if s not in exclude:
                res.append((s, float(self.pop_counts[s])))
            if len(res) >= k:
                break
        return res, None


class SyncHybridWrapper:
    """Wraps HybridRecommendationEngine to expose a sync recommend_top_k for Evaluator."""
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
        
        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(self.engine.predict(req))
        recs = [(r.song_id, r.score) for r in response.recommendations]
        return recs, None


def run_hybrid_eval(dataset_dir="datasets/processed/lastfm"):
    print("Loading datasets...")
    train_df = pd.read_parquet(f"{dataset_dir}/train.parquet")
    test_df = pd.read_parquet(f"{dataset_dir}/test.parquet")
    
    print("\n=== 1. MODEL INITIALIZATION ===")
    weight_cfg = InteractionWeightsConfig(play=1.0)
    builder = DatasetBuilder(weight_cfg)
    train_matrix = builder.fit_transform(f"{dataset_dir}/train.parquet")
    
    als_cfg = ALSConfig(factors=32, regularization=0.01, iterations=15, alpha=1.0)
    model_cf = CollaborativeFilteringModel(als_cfg, builder)
    model_cf.train(train_matrix)
    gen_cf = CandidateGenerator(model_cf)
    
    model_pop = PopularityModelFast(train_df)
    
    user_counts = train_df.groupby('user_id').size().to_dict()
    max_pop = float(max(model_pop.scores.values()))
    
    evaluator = Evaluator(k_values=[5, 10])
    
    print("\n=== 2. EXPERIMENTING HYBRID WEIGHTS (Validation) ===")
    
    # Normally we'd use validation.parquet. 
    # For speed and protocol alignment, we'll run a quick grid on validation data.
    val_df = pd.read_parquet(f"{dataset_dir}/validation.parquet")
    
    configs = {
        "ALS 0.90 / Pop 0.10": {"als": 0.90, "popularity": 0.10, "content": 0.0},
        "ALS 0.80 / Pop 0.20": {"als": 0.80, "popularity": 0.20, "content": 0.0},
        "ALS 0.70 / Pop 0.30": {"als": 0.70, "popularity": 0.30, "content": 0.0},
        "ALS 0.60 / Pop 0.40": {"als": 0.60, "popularity": 0.40, "content": 0.0},
        "ALS 0.50 / Pop 0.50": {"als": 0.50, "popularity": 0.50, "content": 0.0},
    }
    
    best_config_name = None
    best_ndcg = -1
    best_weights = None
    
    for name, weights in configs.items():
        HybridConfig.WEIGHTS_KNOWN_USER = weights
        HybridConfig.WEIGHTS_SPARSE_USER = weights
        HybridConfig.WEIGHTS_NEW_USER = {"als": 0.0, "popularity": 1.0, "content": 0.0}
        
        engine = HybridRecommendationEngine(
            als_model=gen_cf,
            popularity_model=model_pop,
            content_model=None,
            user_interaction_counts=user_counts,
            song_to_artist_map={},
            als_min=-0.5, als_max=1.5,
            max_pop=max_pop,
            content_available=False
        )
        wrapper = SyncHybridWrapper(engine, {})
        metrics = evaluator.evaluate(wrapper, train_df, val_df)
        print(f"Validation [{name}]: NDCG@10 = {metrics['NDCG@10']:.4f}, HitRate@10 = {metrics['HitRate@10']:.4f}")
        
        if metrics['NDCG@10'] > best_ndcg:
            best_ndcg = metrics['NDCG@10']
            best_config_name = name
            best_weights = weights

    print(f"\n=> Best Config selected via Validation: {best_config_name} (Frozen for Final Test)\n")

    print("\n=== 3. FINAL TEST EVALUATION ===")
    HybridConfig.WEIGHTS_KNOWN_USER = best_weights
    HybridConfig.WEIGHTS_SPARSE_USER = best_weights # Could be tuned separately
    
    final_hybrid_engine = HybridRecommendationEngine(
        als_model=gen_cf,
        popularity_model=model_pop,
        content_model=None,
        user_interaction_counts=user_counts,
        song_to_artist_map={},
        als_min=-0.5, als_max=1.5,
        max_pop=max_pop,
        content_available=False
    )
    hybrid_wrapper = SyncHybridWrapper(final_hybrid_engine, {})
    
    results = []
    for name, m in [("Popularity", model_pop), ("ALS", gen_cf), ("Hybrid", hybrid_wrapper)]:
        print(f"Evaluating {name} on test set...")
        metrics = evaluator.evaluate(m, train_df, test_df)
        metrics['Model'] = name
        results.append(metrics)
        
    df_results = pd.DataFrame(results).set_index("Model")
    cols = ["Precision@5", "Precision@10", "Recall@5", "Recall@10", "NDCG@5", "NDCG@10", "HitRate@10", "Coverage", "Diversity"]
    print(df_results[[c for c in cols if c in df_results.columns]].to_markdown())


if __name__ == "__main__":
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    # Run asyncio loop properly
    import nest_asyncio
    nest_asyncio.apply()
    
    run_hybrid_eval()
