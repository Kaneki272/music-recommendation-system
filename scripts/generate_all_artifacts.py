import os
import asyncio
import pandas as pd
from datetime import datetime, timezone

from ml.collaborative.config import InteractionWeightsConfig, ALSConfig
from ml.collaborative.dataset_builder import DatasetBuilder
from ml.collaborative.model import CollaborativeFilteringModel

from ml.popularity.config import PopularityConfig, PopularityMode
from ml.popularity.model import PopularityModel
from ml.contracts.interactions import InteractionDataset, InteractionRecord, InteractionType
from ml.contracts.identifiers import UserId, SongId

from ml.content_based.config import ContentBasedConfig
from ml.content_based.model import ContentBasedModel
from backend.database.qdrant.client import QdrantVectorStore
from feature_store.feast_provider import FeastFeatureProvider

async def main():
    dataset_dir = "datasets/processed/lastfm"
    print("Loading train dataset...")
    train_df = pd.read_parquet(f"{dataset_dir}/train.parquet")
    
    # Generate InteractionDataset for models that require it (Popularity, ContentBased)
    # We take a sample or the whole thing. The whole thing might be large (15M rows).
    # To avoid memory explosion, we can sample the last 1M rows for training profile/popularity.
    print("Building InteractionDataset from parquet...")
    # Map 'interaction_type' to enum
    def map_type(t):
        try:
            return InteractionType(t)
        except:
            return InteractionType.PLAY
            
    # For popularity and content-based, we'll use a subset if it's too large, but let's try the full for popularity
    # To avoid memory issues with 15M objects in python, let's use the most recent 500k interactions
    recent_df = train_df.sort_values('timestamp').tail(500000)
    
    interactions = []
    for _, row in recent_df.iterrows():
        interactions.append(InteractionRecord(
            user_id=UserId(row['user_id']),
            song_id=SongId(row['song_id']),
            interaction_type=map_type(row['interaction_type']),
            timestamp=row['timestamp'].replace(tzinfo=timezone.utc),
            weight=float(row['weight'])
        ))
        
    interaction_dataset = InteractionDataset(
        dataset_version="lastfm_train",
        date_range_start=recent_df['timestamp'].min().replace(tzinfo=timezone.utc),
        date_range_end=recent_df['timestamp'].max().replace(tzinfo=timezone.utc),
        interactions=interactions,
        weight_config_version="v1"
    )
    ref_time = interaction_dataset.date_range_end

    print("\n--- Generating Collaborative Filtering Artifacts ---")
    weight_cfg = InteractionWeightsConfig(play=1.0, complete=0.0, playlist_add=0.0, like=0.0)
    builder = DatasetBuilder(weight_cfg)
    train_matrix = builder.fit_transform(f"{dataset_dir}/train.parquet")
    
    als_cfg = ALSConfig(factors=64, regularization=0.1, iterations=15, alpha=5.0)
    als_model = CollaborativeFilteringModel(als_cfg, builder)
    als_model.train(train_matrix)
    
    os.makedirs("models/collaborative/v1", exist_ok=True)
    als_model.save("models/collaborative/v1")
    print("ALS artifacts saved to models/collaborative/v1")

    print("\n--- Generating Popularity Artifacts ---")
    pop_config = PopularityConfig(mode=PopularityMode.GLOBAL, half_life_days=3650.0)
    pop_model = PopularityModel(pop_config)
    await pop_model.train(interaction_dataset, reference_time=ref_time)
    
    os.makedirs("models/popularity/v1", exist_ok=True)
    await pop_model.save("models/popularity/v1")
    print("Popularity artifacts saved to models/popularity/v1")

    print("\n--- Generating Content-Based Artifacts ---")
    qstore = QdrantVectorStore(collection_name="audio_v2", path="datasets/processed/qdrant_db")
    fp = FeastFeatureProvider(repo_path="feature_store/repo", qdrant_store=qstore)
    cb_config = ContentBasedConfig()
    cb_model = ContentBasedModel(feature_provider=fp, vector_store=qstore, config=cb_config)
    
    await cb_model.train(interaction_dataset, reference_time=ref_time)
    
    os.makedirs("models/content/v1", exist_ok=True)
    await cb_model.save("models/content/v1")
    print("Content-based artifacts saved to models/content/v1")

if __name__ == "__main__":
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    asyncio.run(main())
