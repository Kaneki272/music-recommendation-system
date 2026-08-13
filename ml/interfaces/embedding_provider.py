"""
ML Interface — Vector Store (Qdrant Abstraction)
==================================================
ML models MUST NOT import Qdrant directly.
They depend on this interface so the vector store implementation
can be swapped (Qdrant → Weaviate → Pinecone) without touching model code.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from ml.contracts.identifiers import SongId


class VectorSearchResult(BaseModel if False else object):
    """Result from a nearest-neighbour vector search."""
    def __init__(self, song_id: SongId, score: float, payload: Dict[str, Any] = None):
        self.song_id = song_id
        self.score = score
        self.payload = payload or {}


class VectorStoreInterface(ABC):
    """
    Abstract vector store for song embedding operations.
    Content-Based model uses search(). Training pipeline uses upsert().
    """

    @abstractmethod
    async def upsert(self, song_id: SongId, vector: List[float], payload: Dict[str, Any] = None) -> None:
        """Insert or update a song vector and its metadata payload."""
        pass

    @abstractmethod
    async def batch_upsert(self, records: List[Dict[str, Any]]) -> None:
        """Bulk insert/update. Each record: {song_id, vector, payload}."""
        pass

    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 50,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """Approximate nearest-neighbour search. Returns top_k results."""
        pass

    @abstractmethod
    async def get(self, song_id: SongId) -> Optional[List[float]]:
        """Retrieve a stored vector by song_id."""
        pass

    @abstractmethod
    async def delete(self, song_id: SongId) -> None:
        """Remove a song's vector from the store."""
        pass
