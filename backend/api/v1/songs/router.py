import os
import shutil
import tempfile
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from backend.config.settings import settings
from backend.dependencies.database import get_postgres_db
from backend.models.song import Song
from backend.models.audio_features import AudioFeature
from backend.models.artist import Artist
from backend.models.album import Album
from backend.database.qdrant.client import QdrantVectorStore
from ml.contracts.identifiers import SongId

from backend.services.audio_service import extract_features_for_file, AUDIO_EXTS

router = APIRouter(prefix="/songs", tags=["songs"])

# Bounded CPU execution: Max 2 concurrent extractions to prevent starving the event loop and CPU
extraction_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audio_extractor")

@router.post("/upload")
async def upload_song(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_postgres_db)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Empty filename")
        
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in AUDIO_EXTS:
        raise HTTPException(status_code=400, detail=f"Unsupported audio format. Allowed: {', '.join(AUDIO_EXTS)}")

    # Secure temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    temp_path = temp_file.name
    temp_file.close() # Close so we can write/read safely
    
    max_size_bytes = settings.MAX_AUDIO_UPLOAD_SIZE_MB * 1024 * 1024
    bytes_read = 0
    
    try:
        # Stream file to disk to enforce max size
        with open(temp_path, "wb") as buffer:
            while True:
                chunk = await file.read(8192)
                if not chunk:
                    break
                bytes_read += len(chunk)
                if bytes_read > max_size_bytes:
                    raise HTTPException(status_code=400, detail=f"File exceeds maximum allowed size of {settings.MAX_AUDIO_UPLOAD_SIZE_MB}MB")
                buffer.write(chunk)
                
        if bytes_read == 0:
            raise HTTPException(status_code=400, detail="Empty file")

        # Feature extraction bounded in ThreadPoolExecutor
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(extraction_executor, extract_features_for_file, temp_path)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=f"Audio extraction failed: {result.get('error_msg')}")
            
        song_id = str(result["song_id"])
        
        # PostgreSQL persistence
        dummy_artist_id = uuid.uuid5(uuid.NAMESPACE_OID, "dummy_artist")
        dummy_album_id = uuid.uuid5(uuid.NAMESPACE_OID, "dummy_album")

        # Ensure dummy artist and album exist
        artist = await db.scalar(select(Artist).filter_by(id=dummy_artist_id))
        if not artist:
            artist = Artist(id=dummy_artist_id, name="Unknown Artist")
            db.add(artist)
            
        album = await db.scalar(select(Album).filter_by(id=dummy_album_id))
        if not album:
            album = Album(id=dummy_album_id, title="Unknown Album", artist_id=dummy_artist_id)
            db.add(album)
            
        await db.commit()

        # Check if song exists
        song = await db.scalar(select(Song).filter_by(id=uuid.UUID(song_id)))
        if not song:
            song = Song(
                id=uuid.UUID(song_id),
                title=file.filename,
                album_id=dummy_album_id,
                artist_id=dummy_artist_id,
                duration_ms=int(result["duration"] * 1000)
            )
            db.add(song)
            
        # Audio feature idempotent insert/update
        af = await db.scalar(select(AudioFeature).filter_by(song_id=uuid.UUID(song_id)))
        if not af:
            af = AudioFeature(
                song_id=uuid.UUID(song_id),
                tempo_bpm=result["tempo_bpm"],
                harmonic_ratio=result["harmonic_ratio"],
                vector_dimension=result["feature_dimension"],
                extraction_version=result["extraction_version"]
            )
            db.add(af)
        else:
            if af.extraction_version != result["extraction_version"]:
                af.extraction_version = result["extraction_version"]
                af.tempo_bpm = result["tempo_bpm"]
                af.harmonic_ratio = result["harmonic_ratio"]
                af.vector_dimension = result["feature_dimension"]
        
        await db.commit()
        
        # Qdrant Persistence
        try:
            qstore = QdrantVectorStore(collection_name="audio_features", location=settings.QDRANT_URI)
            await qstore.initialize_collection()
            
            await qstore.upsert(
                song_id=SongId(song_id),
                vector=result["vector"],
                payload={
                    "song_id": song_id,
                    "filename": file.filename,
                    "file_hash": result["file_hash"],
                    "extraction_version": result["extraction_version"],
                    "vector_dimension": result["feature_dimension"]
                }
            )
        except Exception as e:
            # If Qdrant fails, we don't rollback Postgres automatically as it acts as source of truth,
            # but we return 500 so frontend knows it is not fully stored.
            raise HTTPException(status_code=500, detail=f"Qdrant persistence failed: {str(e)}")

        return {
            "success": True,
            "song_id": song_id,
            "feature_dimension": result["feature_dimension"],
            "feature_extracted": True,
            "stored": True
        }
        
    finally:
        # Always cleanup the temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
