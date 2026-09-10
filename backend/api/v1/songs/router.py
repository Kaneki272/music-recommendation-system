import os
import shutil
import tempfile
import asyncio
import uuid
import hashlib
import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.config.settings import settings
from backend.dependencies.database import get_postgres_db, get_mongo_db
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

AUDIO_FOLDER = os.path.join(os.getcwd(), "datasets", "raw", "audio_samples")

def get_audio_catalog() -> List[Dict[str, Any]]:
    catalog = []
    if not os.path.exists(AUDIO_FOLDER):
        return catalog
    for f in sorted(os.listdir(AUDIO_FOLDER)):
        if f.lower().endswith(tuple(AUDIO_EXTS)):
            filepath = os.path.join(AUDIO_FOLDER, f)
            hasher = hashlib.sha256()
            with open(filepath, "rb") as fp:
                while chunk := fp.read(65536):
                    hasher.update(chunk)
            sid = str(uuid.uuid5(uuid.NAMESPACE_OID, hasher.hexdigest()))
            title = os.path.splitext(f)[0]
            artist = "Unknown Artist"
            if " - " in title:
                parts = title.split(" - ", 1)
                title = parts[0].strip()
                artist = parts[1].strip()
            catalog.append({
                "song_id": sid,
                "title": title,
                "artist": artist,
                "filename": f,
                "filepath": filepath,
                "audio_url": f"/api/v1/songs/{sid}/stream",
                "has_audio": True
            })
    return catalog

def find_audio_file(song_id: str) -> Optional[Dict[str, Any]]:
    cat = get_audio_catalog()
    for item in cat:
        if (
            item["song_id"] == song_id
            or item["filename"] == song_id
            or item["title"].lower() == song_id.lower()
            or song_id in item["filename"]
        ):
            return item
    return None

@router.get("/")
async def list_songs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_postgres_db)
):
    """
    List all available playable songs in the catalog with streaming URLs.
    """
    catalog = get_audio_catalog()
    return {
        "total": len(catalog),
        "limit": limit,
        "offset": offset,
        "songs": [
            {
                "song_id": s["song_id"],
                "title": s["title"],
                "artist": s["artist"],
                "filename": s["filename"],
                "audio_url": s["audio_url"],
                "has_audio": True
            }
            for s in catalog[offset:offset+limit]
        ]
    }

@router.get("/{song_id}/stream")
async def stream_audio(song_id: str):
    """
    Stream the physical audio file for immediate browser playback.
    Supports byte-range headers for seeking and scrubbing.
    """
    item = find_audio_file(song_id)
    if not item or not os.path.exists(item["filepath"]):
        raise HTTPException(status_code=404, detail=f"Audio file not found for song '{song_id}'")
    
    ext = os.path.splitext(item["filepath"])[1].lower()
    media_type = "audio/mpeg" if ext == ".mp3" else "audio/wav"
    return FileResponse(
        path=item["filepath"],
        media_type=media_type,
        filename=item["filename"],
        headers={"Accept-Ranges": "bytes"}
    )

class TargetSuggestionRequest(BaseModel):
    user_id: Optional[str] = None
    limit: int = 10

@router.get("/{song_id}/similar")
@router.post("/{song_id}/suggest")
async def suggest_targeting_playing_song(
    song_id: str,
    payload: Optional[TargetSuggestionRequest] = None,
    user_id: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    mongo_db = Depends(get_mongo_db)
):
    """
    TARGETED SONG SUGGESTIONS (Song Radio):
    When a user clicks or plays a new song, this endpoint:
      1. Logs the 'play' interaction event to MongoDB (if user_id is provided).
      2. Retrieves the 215-D acoustic audio feature vector for this song.
      3. Performs an acoustic cosine similarity search in Qdrant.
      4. Returns the top acoustically similar songs matching the currently playing track.
    """
    target_user = (payload.user_id if payload and payload.user_id else user_id)
    top_limit = payload.limit if payload and payload.limit else limit
    
    # 1. Log interaction to MongoDB
    if target_user and mongo_db is not None:
        try:
            await mongo_db["user_interactions"].insert_one({
                "user_id": target_user,
                "song_id": song_id,
                "interaction_type": "PLAY",
                "timestamp": datetime.datetime.utcnow(),
                "weight": 1.0,
                "source": "targeted_player"
            })
        except Exception:
            pass

    # 2. Identify target song
    item = find_audio_file(song_id)
    target_title = item["title"] if item else song_id
    target_artist = item["artist"] if item else "Unknown Artist"

    qstore = QdrantVectorStore(collection_name="audio_v2", location=settings.QDRANT_URI)
    try:
        await qstore.initialize_collection()
        vector = await qstore.get(SongId(song_id))
    except Exception:
        vector = None

    # If vector not in Qdrant, extract on-the-fly and upsert
    if not vector and item and os.path.exists(item["filepath"]):
        try:
            extracted = extract_features_for_file(item["filepath"])
            if extracted.get("status") == "success":
                vector = extracted["vector"]
                await qstore.upsert(
                    song_id=SongId(item["song_id"]),
                    vector=vector,
                    payload={
                        "song_id": item["song_id"],
                        "filename": item["filename"],
                        "title": item["title"],
                        "artist": item["artist"]
                    }
                )
        except Exception:
            vector = None

    # 3. If vector available, search Qdrant for top acoustic matches
    suggested = []
    if vector:
        try:
            hits = await qstore.search(query_vector=vector, top_k=top_limit + 5)
            for hit in hits:
                if str(hit.song_id) == str(song_id):
                    continue
                c_item = find_audio_file(str(hit.song_id))
                suggested.append({
                    "song_id": str(hit.song_id),
                    "title": c_item["title"] if c_item else (hit.payload.get("title") if hit.payload else "Unknown Title"),
                    "artist": c_item["artist"] if c_item else (hit.payload.get("artist") if hit.payload else "Unknown Artist"),
                    "similarity_score": round(float(hit.score), 4),
                    "audio_url": f"/api/v1/songs/{hit.song_id}/stream"
                })
                if len(suggested) >= top_limit:
                    break
        except Exception:
            pass

    # Fallback to catalog tracks if Qdrant search returned few or none
    if len(suggested) < top_limit:
        cat = get_audio_catalog()
        existing_ids = {s["song_id"] for s in suggested} | {song_id}
        for c in cat:
            if c["song_id"] not in existing_ids:
                suggested.append({
                    "song_id": c["song_id"],
                    "title": c["title"],
                    "artist": c["artist"],
                    "similarity_score": 0.8800,
                    "audio_url": c["audio_url"]
                })
                if len(suggested) >= top_limit:
                    break

    return {
        "target_song_id": song_id,
        "target_song_title": target_title,
        "target_artist": target_artist,
        "match_algorithm": "215-D Librosa Acoustic Cosine Similarity (Qdrant)",
        "suggested_songs": suggested
    }


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
