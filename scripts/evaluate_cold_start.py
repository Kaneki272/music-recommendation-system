import pandas as pd
import os
import asyncio
from scripts.evaluate_hybrid import run_hybrid_eval, PopularityModelFast, SyncHybridWrapper
from ml.collaborative.config import InteractionWeightsConfig, ALSConfig
from ml.collaborative.dataset_builder import DatasetBuilder
from ml.collaborative.model import CollaborativeFilteringModel
from ml.collaborative.candidate_generator import CandidateGenerator
from ml.collaborative.evaluator import Evaluator
from ml.hybrid.engine import HybridRecommendationEngine
from ml.hybrid.config import HybridConfig

def evaluate_cold_start():
    dataset_dir = "datasets/processed/lastfm"
    train_df = pd.read_parquet(f"{dataset_dir}/train.parquet")
    test_df = pd.read_parquet(f"{dataset_dir}/test.parquet")
    
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
    
    # Use the best weights from validation
    best_weights = {"als": 0.90, "popularity": 0.10, "content": 0.0}
    HybridConfig.WEIGHTS_KNOWN_USER = best_weights
    HybridConfig.WEIGHTS_SPARSE_USER = best_weights
    
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
    hybrid_wrapper = SyncHybridWrapper(engine, {})
    
    # Split test users
    test_users = set(test_df['user_id'].unique())
    train_users = set(train_df['user_id'].unique())
    
    new_users = test_users - train_users
    known_users = test_users.intersection(train_users)
    sparse_users = {u for u in known_users if user_counts.get(u, 0) < 5}
    returning_users = {u for u in known_users if user_counts.get(u, 0) >= 5}
    
    test_new = test_df[test_df['user_id'].isin(new_users)]
    test_sparse = test_df[test_df['user_id'].isin(sparse_users)]
    test_known = test_df[test_df['user_id'].isin(returning_users)]
    
    evaluator = Evaluator(k_values=[5, 10])
    
    print("\n--- NEW USERS ---")
    if len(test_new) > 0:
        m = evaluator.evaluate(hybrid_wrapper, train_df, test_new)
        print(f"NDCG@10: {m['NDCG@10']:.4f}, HitRate@10: {m['HitRate@10']:.4f}")
    else:
        print("No new users in test set.")
        
    print("\n--- SPARSE USERS (<5) ---")
    if len(test_sparse) > 0:
        m = evaluator.evaluate(hybrid_wrapper, train_df, test_sparse)
        print(f"NDCG@10: {m['NDCG@10']:.4f}, HitRate@10: {m['HitRate@10']:.4f}")
    else:
        print("No sparse users in test set.")
        
    print("\n--- KNOWN USERS (>=5) ---")
    if len(test_known) > 0:
        m = evaluator.evaluate(hybrid_wrapper, train_df, test_known)
        print(f"NDCG@10: {m['NDCG@10']:.4f}, HitRate@10: {m['HitRate@10']:.4f}")
    else:
        print("No known users in test set.")

if __name__ == "__main__":
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    import nest_asyncio
    nest_asyncio.apply()
    evaluate_cold_start()
