"""
Tests for Qdrant Vector Store Implementation
============================================
Note: These tests mock the qdrant client to ensure logic is correct
without requiring a live Qdrant instance.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.database.qdrant.client import QdrantVectorStore
from ml.contracts.identifiers import SongId, CANONICAL_VECTOR_DIMENSION

@pytest.fixture
def mock_qdrant_client():
    mock = AsyncMock()
    return mock

@pytest.fixture
def qdrant_store(mock_qdrant_client, monkeypatch):
    monkeypatch.setattr("backend.database.qdrant.client.AsyncQdrantClient", lambda **kwargs: mock_qdrant_client)
    return QdrantVectorStore(collection_name="test_audio_v1")

@pytest.mark.asyncio
async def test_upsert_valid_vector(qdrant_store, mock_qdrant_client):
    song_id = SongId("123e4567-e89b-12d3-a456-426614174000")
    valid_vector = [0.1] * CANONICAL_VECTOR_DIMENSION
    payload = {"extraction_version": "v1.0.0"}
    
    await qdrant_store.upsert(song_id, valid_vector, payload)
    
    mock_qdrant_client.upsert.assert_called_once()
    kwargs = mock_qdrant_client.upsert.call_args.kwargs
    assert kwargs["collection_name"] == "test_audio_v1"
    assert len(kwargs["points"]) == 1
    point = kwargs["points"][0]
    assert point.id == song_id
    assert point.vector == valid_vector
    assert point.payload == payload

@pytest.mark.asyncio
async def test_upsert_invalid_dimension_raises_error(qdrant_store):
    song_id = SongId("123")
    invalid_vector = [0.1] * 100  # Wrong dimension
    
    with pytest.raises(ValueError, match=f"Vector dimension must be {CANONICAL_VECTOR_DIMENSION}"):
        await qdrant_store.upsert(song_id, invalid_vector)
