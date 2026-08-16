"""
Qdrant Vector Store Implementation
====================================
Implements the VectorStoreInterface for Qdrant.
Stores the 222-dimensional audio_v1 embeddings.
"""
from typing import List, Optional, Dict, Any
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as rest
from qdrant_client.http.exceptions import UnexpectedResponse

from ml.interfaces.embedding_provider import VectorStoreInterface, VectorSearchResult
from ml.contracts.identifiers import SongId, CANONICAL_VECTOR_DIMENSION


class QdrantVectorStore(VectorStoreInterface):
    """
    Qdrant implementation of the Vector Store.
    Manages connections and collection lifecycle.
    """
    def __init__(self, host: str = "localhost", port: int = 6333, collection_name: str = "audio_v1", location: Optional[str] = None):
        if location:
            self.client = AsyncQdrantClient(location=location)
        else:
            self.client = AsyncQdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self.dimension = CANONICAL_VECTOR_DIMENSION

    async def initialize_collection(self) -> None:
        """Create the collection if it doesn't exist."""
        try:
            await self.client.get_collection(self.collection_name)
        except (UnexpectedResponse, ValueError):
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=rest.VectorParams(
                    size=self.dimension,
                    distance=rest.Distance.COSINE
                )
            )

    async def upsert(self, song_id: SongId, vector: List[float], payload: Dict[str, Any] = None) -> None:
        if len(vector) != self.dimension:
            raise ValueError(f"Vector dimension must be {self.dimension}")
            
        await self.client.upsert(
            collection_name=self.collection_name,
            points=[
                rest.PointStruct(
                    id=song_id,  # Qdrant supports UUID strings directly
                    vector=vector,
                    payload=payload or {}
                )
            ]
        )

    async def batch_upsert(self, records: List[Dict[str, Any]]) -> None:
        points = []
        for r in records:
            if len(r["vector"]) != self.dimension:
                raise ValueError(f"Vector dimension must be {self.dimension}")
            points.append(
                rest.PointStruct(
                    id=r["song_id"],
                    vector=r["vector"],
                    payload=r.get("payload", {})
                )
            )
            
        if points:
            await self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )

    async def search(
        self,
        query_vector: List[float],
        top_k: int = 50,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        qdrant_filter = None
        if filters:
            # Simple match filter conversion for Qdrant
            must_conditions = [
                rest.FieldCondition(key=k, match=rest.MatchValue(value=v))
                for k, v in filters.items()
            ]
            qdrant_filter = rest.Filter(must=must_conditions)

        hits = await self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=qdrant_filter,
            limit=top_k
        )
        
        return [
            VectorSearchResult(
                song_id=SongId(hit.id),
                score=hit.score,
                payload=hit.payload
            ) for hit in hits
        ]

    async def get(self, song_id: SongId) -> Optional[List[float]]:
        points = await self.client.retrieve(
            collection_name=self.collection_name,
            ids=[song_id],
            with_vectors=True
        )
        if not points:
            return None
        return points[0].vector

    async def delete(self, song_id: SongId) -> None:
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=rest.PointIdsList(points=[song_id])
        )
