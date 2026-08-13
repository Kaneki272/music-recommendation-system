"""
Sync Pipeline: Postgres -> Qdrant (Audio Vectors)
===================================================
Reads processed audio features from PostgreSQL and upserts them
into Qdrant. Future-proofed to be triggered via Kafka events.
"""
from typing import List, Dict, Any
from backend.database.qdrant.client import QdrantVectorStore
from ml.contracts.identifiers import SongId

class AudioFeatureSyncJob:
    def __init__(self, qdrant_store: QdrantVectorStore):
        self.qdrant = qdrant_store

    async def process_batch(self, batch: List[Dict[str, Any]]):
        """
        Takes a batch of AudioFeature dictionaries (from Postgres or Kafka)
        and upserts them to Qdrant.
        
        Expected structure per item:
        {
            "song_id": "uuid",
            "audio_feature_vector": [float],
            "extraction_version": "v1",
            ...
        }
        """
        records = []
        for item in batch:
            records.append({
                "song_id": SongId(item["song_id"]),
                "vector": item["audio_feature_vector"],
                "payload": {
                    "extraction_version": item.get("extraction_version", "v1.0.0"),
                    "preprocessing_version": item.get("preprocessing_version", "v1.0.0"),
                    "created_at": item.get("created_at")
                }
            })
            
        await self.qdrant.batch_upsert(records)
