import os
import sys
import json
import uuid
import shutil
import asyncio
from datetime import datetime
import pandas as pd
import motor.motor_asyncio
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ml.collaborative.config import ALSConfig, InteractionWeightsConfig
from ml.collaborative.dataset_builder import DatasetBuilder
from ml.collaborative.model import CollaborativeFilteringModel
from ml.collaborative.evaluator import Evaluator
from ml.collaborative.candidate_generator import CandidateGenerator
from backend.config.settings import settings

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models", "als")
ACTIVE_FILE = os.path.join(MODELS_DIR, "active.json")

async def extract_data(db) -> pd.DataFrame:
    """Extract interactions from MongoDB."""
    print("Extracting interactions from MongoDB...")
    cursor = db["user_interactions"].find({"interaction_type": {"$exists": True}})
    records = await cursor.to_list(length=None)
    if not records:
        return pd.DataFrame()
    
    df = pd.DataFrame(records)
    if "_id" in df.columns:
        df = df.drop(columns=["_id"])
    return df

def temporal_split(df: pd.DataFrame, split_ratio: float = 0.8) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Splits interactions temporally."""
    print("Performing temporal split...")
    df = df.sort_values("timestamp")
    split_idx = int(len(df) * split_ratio)
    train_df = df.iloc[:split_idx].copy()
    val_df = df.iloc[split_idx:].copy()
    return train_df, val_df

async def main():
    mongo_client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGO_URI)
    db = mongo_client[settings.MONGO_DATABASE]
    
    # 1. Extraction
    df = await extract_data(db)
    if df.empty:
        print("No interactions found. Aborting.")
        return
        
    # Ensure weight is present if missing
    if "weight" not in df.columns:
        df["weight"] = 1.0

    print(f"Extracted {len(df)} interactions.")

    # 2. Validation / Filtering
    # Only keep users and items with at least 5 interactions (to avoid pure noise in training)
    user_counts = df['user_id'].value_counts()
    song_counts = df['song_id'].value_counts()
    
    valid_users = user_counts[user_counts >= 5].index
    valid_songs = song_counts[song_counts >= 5].index
    
    df = df[df['user_id'].isin(valid_users) & df['song_id'].isin(valid_songs)]
    print(f"After filtering (>=5 interactions), {len(df)} interactions remain.")
    
    if df.empty:
         print("Not enough data to train. Aborting.")
         return

    # 3. Temporal Split
    train_df, val_df = temporal_split(df)
    
    # 4. Dump train_df to parquet for DatasetBuilder
    tmp_parquet = "tmp_train.parquet"
    table = pa.Table.from_pandas(train_df)
    pq.write_table(table, tmp_parquet)
    
    # 5. Build matrix
    weight_config = InteractionWeightsConfig()
    builder = DatasetBuilder(weight_config=weight_config)
    print("Building user-item matrix...")
    train_matrix = builder.fit_transform(tmp_parquet)
    
    # Cleanup tmp
    if os.path.exists(tmp_parquet):
        os.remove(tmp_parquet)
        
    print(f"Matrix shape: {train_matrix.shape} | Density: {train_matrix.nnz / (train_matrix.shape[0] * train_matrix.shape[1]):.6f}")

    # 6. Train ALS
    als_config = ALSConfig()
    model = CollaborativeFilteringModel(als_config, builder)
    print("Training Implicit ALS model...")
    model.train(train_matrix)
    
    # 7. Evaluate Candidate
    print("Evaluating candidate model on validation set...")
    evaluator = Evaluator(k_values=[5, 10])
    
    # Wrap model with CandidateGenerator for the evaluator
    candidate_generator = CandidateGenerator(model)
    
    # Monkey-patch recommend_top_k into model for evaluator to use
    model.recommend_top_k = candidate_generator.recommend_top_k
    
    candidate_metrics = evaluator.evaluate(model, train_df, val_df)
    for k, v in candidate_metrics.items():
        print(f"Candidate {k}: {v:.4f}")
        
    # 8. Evaluation Gate (vs Active Production Model)
    promote = True
    active_metrics = {}
    if os.path.exists(ACTIVE_FILE):
        with open(ACTIVE_FILE, "r") as f:
            active_info = json.load(f)
            
        active_version = active_info.get("active_version")
        active_path = os.path.join(MODELS_DIR, active_version)
        if os.path.exists(active_path):
            try:
                print(f"Evaluating active model ({active_version}) on the same validation set...")
                active_model = CollaborativeFilteringModel.load(active_path)
                active_cg = CandidateGenerator(active_model)
                active_model.recommend_top_k = active_cg.recommend_top_k
                active_metrics = evaluator.evaluate(active_model, train_df, val_df)
                
                for k, v in active_metrics.items():
                    print(f"Active {k}: {v:.4f}")
                    
                # Gate Logic:
                # Promote if Candidate NDCG@10 >= Active NDCG@10 - 0.05 (allowing slight variance, but ideally >=)
                if candidate_metrics.get("NDCG@10", 0) >= active_metrics.get("NDCG@10", 0) * 0.95:
                    print("Candidate passes evaluation gate.")
                else:
                    print("Candidate failed to beat or match active model. REJECTING.")
                    promote = False
            except Exception as e:
                print(f"Could not load or evaluate active model: {e}. Promoting candidate by default.")
        
    # 9. Version and Promote
    new_version = f"v_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:6]}"
    version_dir = os.path.join(MODELS_DIR, new_version)
    
    # Always save the candidate
    print(f"Saving candidate model to {version_dir}")
    model.save(version_dir)
    
    metadata = {
        "model_version": new_version,
        "trained_at": datetime.now().isoformat(),
        "training_users": len(builder.user_mapping),
        "training_items": len(builder.song_mapping),
        "training_interactions": len(train_df),
        "factors": als_config.factors,
        "iterations": als_config.iterations,
        "metrics": candidate_metrics
    }
    
    with open(os.path.join(version_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
        
    if promote:
        print(f"Promoting {new_version} to active.")
        with open(ACTIVE_FILE, "w") as f:
            json.dump({
                "active_version": new_version,
                "promoted_at": datetime.now().isoformat()
            }, f, indent=2)
    else:
        print(f"Model {new_version} archived but not promoted.")
        
    mongo_client.close()
    
if __name__ == "__main__":
    asyncio.run(main())
