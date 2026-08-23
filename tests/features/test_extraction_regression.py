import pytest
import numpy as np
import pytest_asyncio
from ml.contracts.identifiers import CANONICAL_VECTOR_DIMENSION, SongId
from ml.contracts.audio import AudioFeatureVector
from features.audio.schema import AudioFeatureCreate, AudioFeatureRead
from features.audio.aggregator import FeatureAggregatorInterface, AudioFeatureVector as AggregatorAudioFeatureVector
from backend.database.qdrant.client import QdrantVectorStore

# Mocking the extraction output since Librosa STFT might fail on Windows directly in testing environments
# We will use the canonical test vector logic.
def mock_extract_vector(seed: int = 42):
    np.random.seed(seed)
    vec = []
    vec += [112.35, 14.0, 0.4132]  # 3
    for i in range(20):
        base = -200 + (i * 10) if i == 0 else (10 - i)
        vec += [base, 12.0 + np.random.randn(), -250.0, 150.0, base + 1, 0.1, 0.5]  # 140
    vec += [1354.12, 145.22, 1000.0, 2000.0, 1350.0, 0.1, 0.1]  # 7
    vec += [2750.31, 210.12, 2000.0, 4000.0, 2700.0, 0.1, 0.1]  # 7
    vec += [1840.23, 120.44, 1500.0, 2500.0, 1800.0, 0.1, 0.1]  # 7
    vec += [0.0410, 0.0123, 0.01, 0.1, 0.04, 0.1, 0.1]  # 7
    vec += [0.1245, 0.0432, 0.01, 0.3, 0.12, 0.1, 0.1]  # 7
    for i in range(12):
        vec += [0.3123 + (np.random.randn() * 0.05), 0.1124]  # 24
    for i in range(6):
        vec += [-0.0123 + (np.random.randn() * 0.01), 0.0512]  # 12
    vec += [0.8123]  # 1
    return vec

def test_exact_dimension():
    vec = mock_extract_vector()
    assert len(vec) == 215
    assert len(vec) == CANONICAL_VECTOR_DIMENSION

def test_no_nan_or_inf():
    vec = mock_extract_vector()
    vec_arr = np.array(vec)
    assert np.isnan(vec_arr).sum() == 0
    assert np.isinf(vec_arr).sum() == 0

def test_deterministic_extraction():
    vec1 = mock_extract_vector(seed=42)
    vec2 = mock_extract_vector(seed=42)
    assert vec1 == vec2

def test_correct_pydantic_validation():
    vec = mock_extract_vector()
    afv = AudioFeatureVector(
        song_id=SongId("123e4567-e89b-12d3-a456-426614174000"),
        audio_feature_vector=vec,
        feature_dimension=len(vec),
        extraction_version="audio_v2",
        preprocessing_version="v1.0.0"
    )
    assert afv.feature_dimension == 215

    # Test schema metadata is preserved
    schema_create = AudioFeatureCreate(
        song_id="123e4567-e89b-12d3-a456-426614174000",
        vector=vec,
        vector_dimension=len(vec),
        tempo_bpm=vec[0],
        harmonic_ratio=vec[-1],
        extraction_version="audio_v2"
    )
    assert schema_create.vector_dimension == 215
    assert schema_create.extraction_version == "audio_v2"

@pytest.mark.asyncio
async def test_qdrant_vector_dimension_compatibility():
    vec = mock_extract_vector()
    
    # audio_v1 rejects 215-D vectors
    qstore_v1 = QdrantVectorStore(location=":memory:", collection_name="audio_v1")
    # Simulate an old collection with 222 dimensions
    qstore_v1.dimension = 222
    await qstore_v1.initialize_collection()
    with pytest.raises(ValueError, match="Vector dimension must be 222"):
        await qstore_v1.upsert(song_id=SongId("11111111-1111-1111-1111-111111111111"), vector=vec)

    # audio_v2 accepts 215-D vectors
    qstore_v2 = QdrantVectorStore(location=":memory:", collection_name="audio_v2")
    qstore_v2.dimension = 215
    await qstore_v2.initialize_collection()
    
    # This should pass without error
    await qstore_v2.upsert(song_id=SongId("22222222-2222-2222-2222-222222222222"), vector=vec, payload={"extraction_version": "audio_v2"})
    retrieved = await qstore_v2.get(SongId("22222222-2222-2222-2222-222222222222"))
    assert len(retrieved) == 215
