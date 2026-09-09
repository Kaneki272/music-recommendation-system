import pytest
import os
import wave
import uuid
from fastapi.testclient import TestClient
from backend.main import app
from backend.dependencies.database import get_postgres_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models.song import Song
from backend.models.audio_features import AudioFeature
from backend.config.settings import settings
from backend.database.qdrant.client import QdrantVectorStore
from ml.contracts.identifiers import SongId
import hashlib
import asyncio

# Setup DB tables for test using asyncpg
from sqlalchemy.ext.asyncio import create_async_engine
from backend.models.base import Base

async def setup_db():
    engine = create_async_engine(settings.POSTGRES_URI)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
loop.run_until_complete(setup_db())

client = TestClient(app)

@pytest.fixture(scope="module")
def valid_wav_file(tmp_path_factory):
    # Generate a simple valid wav file with some noise/sine to avoid NaNs in librosa
    import math
    import struct
    fn = tmp_path_factory.mktemp("data") / "test_valid.wav"
    path = str(fn)
    with wave.open(path, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        # write 1 second of a 440Hz sine wave
        frames = []
        for i in range(22050):
            value = int(32767.0 * math.sin(2.0 * math.pi * 440.0 * i / 22050.0))
            frames.append(struct.pack('<h', value))
        wav_file.writeframes(b''.join(frames))
    yield path
    if os.path.exists(path):
        os.remove(path)

@pytest.fixture(scope="module")
def corrupt_wav_file(tmp_path_factory):
    fn = tmp_path_factory.mktemp("data") / "test_corrupt.wav"
    path = str(fn)
    with open(path, 'wb') as f:
        f.write(b"NOT A WAV FILE")
    yield path
    if os.path.exists(path):
        os.remove(path)

def test_upload_valid_audio(valid_wav_file):
    with TestClient(app) as client:
        with open(valid_wav_file, 'rb') as f:
            response = client.post("/api/v1/songs/upload", files={"file": ("test_valid.wav", f, "audio/wav")})
        
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "song_id" in data
    assert data["feature_dimension"] == 215
    assert data["feature_extracted"] is True
    assert data["stored"] is True
    
    song_id = data["song_id"]
    
    # 6. Verify feature dimension and DB persistence using real infrastructure
    # Since we can't easily run async code in this sync test function without a custom loop,
    # we'll use an async helper block.
    async def verify_db():
        from backend.dependencies.database import postgres_session_factory
        async with postgres_session_factory() as session:
            song = await session.scalar(select(Song).filter_by(id=uuid.UUID(song_id)))
            assert song is not None, "Song record was not created"
            
            af = await session.scalar(select(AudioFeature).filter_by(song_id=uuid.UUID(song_id)))
            assert af is not None, "AudioFeature record was not created"
            assert af.vector_dimension == 215
            assert af.extraction_version == "audio_v2"
            
        qstore = QdrantVectorStore(collection_name="audio_features", location=settings.QDRANT_URI)
        vector = await qstore.get(SongId(song_id))
        assert vector is not None, "Vector not found in Qdrant"
        assert len(vector) == 215, "Vector dimension in Qdrant is not 215"
        
    # We must run it using the existing event loop or a new one
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(verify_db())

def test_upload_unsupported_format(valid_wav_file):
    # Rename to .txt
    temp_txt = valid_wav_file.replace(".wav", ".txt")
    import shutil
    shutil.copy(valid_wav_file, temp_txt)
    
    with TestClient(app) as client:
        with open(temp_txt, 'rb') as f:
            response = client.post("/api/v1/songs/upload", files={"file": ("test_valid.txt", f, "text/plain")})
        
    assert response.status_code == 400
    assert "Unsupported audio format" in response.json()["detail"]
    os.remove(temp_txt)

def test_upload_empty_file():
    with TestClient(app) as client:
        response = client.post("/api/v1/songs/upload", files={"file": ("empty.wav", b"", "audio/wav")})
    assert response.status_code == 400
    assert "Empty file" in response.json()["detail"]

def test_upload_deterministic_id(valid_wav_file):
    with TestClient(app) as client:
        with open(valid_wav_file, 'rb') as f:
            response1 = client.post("/api/v1/songs/upload", files={"file": ("test_valid.wav", f, "audio/wav")})
        
        with open(valid_wav_file, 'rb') as f:
            response2 = client.post("/api/v1/songs/upload", files={"file": ("test_valid_copy.wav", f, "audio/wav")})
        
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    # ID must be exactly the same
    assert response1.json()["song_id"] == response2.json()["song_id"]

def test_upload_corrupt_audio(corrupt_wav_file):
    with TestClient(app) as client:
        with open(corrupt_wav_file, 'rb') as f:
            response = client.post("/api/v1/songs/upload", files={"file": ("test_corrupt.wav", f, "audio/wav")})
        
    assert response.status_code == 400
    assert "Audio extraction failed" in response.json()["detail"]

