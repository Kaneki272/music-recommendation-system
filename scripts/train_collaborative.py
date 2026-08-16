import argparse
import pandas as pd
from ml.collaborative.config import InteractionWeightsConfig, ALSConfig
from ml.collaborative.dataset_builder import DatasetBuilder
from ml.collaborative.model import CollaborativeFilteringModel
from ml.collaborative.candidate_generator import CandidateGenerator
from ml.collaborative.evaluator import Evaluator

def run_hyperparameter_tuning(dataset_dir="datasets/processed/lastfm"):
    print("Running ALS Hyperparameter Tuning on Validation Set...")
    
    # Load data
    train_df = pd.read_parquet(f"{dataset_dir}/train.parquet")
    val_df = pd.read_parquet(f"{dataset_dir}/validation.parquet")
    
    # For Last.fm, we only have play events
    weight_cfg = InteractionWeightsConfig(play=1.0, complete=0.0, playlist_add=0.0, like=0.0)
    builder = DatasetBuilder(weight_cfg)
    print("Building sparse matrix...")
    train_matrix = builder.fit_transform(f"{dataset_dir}/train.parquet")
    
    experiments = [
        ALSConfig(factors=32, regularization=0.01, iterations=15, alpha=1.0),
        ALSConfig(factors=64, regularization=0.1, iterations=15, alpha=5.0),
        ALSConfig(factors=128, regularization=1.0, iterations=30, alpha=20.0)
    ]
    
    evaluator = Evaluator(k_values=[5, 10])
    results = []
    
    for i, als_cfg in enumerate(experiments):
        name = f"F:{als_cfg.factors} R:{als_cfg.regularization} A:{als_cfg.alpha} I:{als_cfg.iterations}"
        print(f"\n--- Training {name} ---")
        
        model = CollaborativeFilteringModel(als_cfg, builder)
        model.train(train_matrix)
        
        generator = CandidateGenerator(model)
        
        metrics = evaluator.evaluate(generator, train_df, val_df)
        metrics['Config'] = name
        results.append(metrics)
        print(f"NDCG@10: {metrics['NDCG@10']:.4f} | Recall@10: {metrics['Recall@10']:.4f}")
        
    df_results = pd.DataFrame(results).set_index("Config")
    print("\n=== Validation Hyperparameter Results ===")
    print(df_results)
    
if __name__ == "__main__":
    import os
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", type=str, default="datasets/processed/lastfm")
    args = parser.parse_args()
    run_hyperparameter_tuning(args.dir)
