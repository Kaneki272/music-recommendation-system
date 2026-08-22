import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
import pandas as pd

from ml.collaborative.config import InteractionWeightsConfig, ALSConfig
from ml.collaborative.dataset_builder import DatasetBuilder
from ml.collaborative.model import CollaborativeFilteringModel
from ml.collaborative.candidate_generator import CandidateGenerator
from ml.collaborative.evaluator import Evaluator

class PopularityModel:
    def __init__(self, train_df):
        self.pop = train_df.groupby('song_id').size().sort_values(ascending=False).index.tolist()
    def recommend_top_k(self, user_id, k, exclude_song_ids=None):
        exclude = set(exclude_song_ids or [])
        res = []
        for s in self.pop:
            if s not in exclude:
                res.append((s, 1.0))
            if len(res) >= k:
                break
        return res, None

class ContentBasedModel:
    def __init__(self):
        # We have NO genuine audio embeddings for the Last.fm dataset.
        # User explicitly forbid fabricating mock embeddings.
        self.valid_tracks = set()
        
    def recommend_top_k(self, user_id, k, exclude_song_ids=None):
        return [], None

def evaluate_cross_model(dataset_dir="datasets/processed/lastfm"):
    print(f"Loading data from {dataset_dir}...")
    train_df = pd.read_parquet(f"{dataset_dir}/train.parquet")
    test_df = pd.read_parquet(f"{dataset_dir}/test.parquet")
    
    evaluator = Evaluator(k_values=[5, 10])
    
    # 1. ALS 
    weight_cfg = InteractionWeightsConfig(play=1.0, complete=0.0, playlist_add=0.0, like=0.0)
    builder = DatasetBuilder(weight_cfg)
    train_matrix = builder.fit_transform(f"{dataset_dir}/train.parquet")
    
    # Use best params from tuning (Assuming 64 factors, 0.1 reg, 15 iter based on standard)
    als_cfg = ALSConfig(factors=64, regularization=0.1, iterations=15, alpha=1.0)
    model_cf = CollaborativeFilteringModel(als_cfg, builder)
    model_cf.train(train_matrix)
    gen_cf = CandidateGenerator(model_cf)
    
    # 2. Popularity
    model_pop = PopularityModel(train_df)
    
    # 3. Content-Based
    model_cb = ContentBasedModel()
    
    # --- EVALUATION A: Full Catalog ---
    print("\n=== A. Full-Catalog Comparison ===")
    results_a = []
    for name, m in [("Popularity", model_pop), ("Collaborative Filtering (ALS)", gen_cf)]:
        metrics = evaluator.evaluate(m, train_df, test_df)
        metrics['Model'] = name
        results_a.append(metrics)
        
    df_a = pd.DataFrame(results_a).set_index("Model")
    cols = ["Precision@5", "Precision@10", "Recall@5", "Recall@10", "NDCG@5", "NDCG@10", "HitRate@10", "Coverage", "Diversity"]
    print(df_a[[c for c in cols if c in df_a.columns]].to_markdown())
    
    # --- EVALUATION B: Content-Eligible ---
    print("\n=== B. Content-Eligible Comparison ===")
    eligible_test_items = test_df[test_df['song_id'].isin(model_cb.valid_tracks)]
    content_coverage = len(model_cb.valid_tracks) / len(train_df['song_id'].unique()) if len(train_df['song_id'].unique()) > 0 else 0
    
    print(f"Total Test Tracks: {len(test_df['song_id'].unique())}")
    print(f"Tracks with Valid Content Features: {len(model_cb.valid_tracks)}")
    print(f"Content Coverage Percentage: {content_coverage*100:.2f}%\n")
    
    if len(eligible_test_items) == 0:
        print("Skipping Content-Based evaluation: 0 eligible content items (No mock embeddings fabricated).")
    else:
        results_b = []
        for name, m in [("Popularity", model_pop), ("Content-Based", model_cb), ("Collaborative Filtering (ALS)", gen_cf)]:
            metrics = evaluator.evaluate(m, train_df, eligible_test_items)
            metrics['Model'] = name
            results_b.append(metrics)
        df_b = pd.DataFrame(results_b).set_index("Model")
        print(df_b[[c for c in cols if c in df_b.columns]].to_markdown())

if __name__ == "__main__":
    import os
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", type=str, default="datasets/processed/lastfm")
    args = parser.parse_args()
    evaluate_cross_model(args.dir)
