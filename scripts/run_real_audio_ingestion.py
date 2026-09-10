import os
import sys
import glob
import time
import uuid
import hashlib
import json
import asyncio
import numpy as np
import librosa
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import Dict, Any, List

# Setup SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models.base import Base
from backend.models.audio_features import AudioFeature
from backend.models.song import Song
from backend.models.album import Album
from backend.models.artist import Artist

# Setup Qdrant
from backend.database.qdrant.client import QdrantVectorStore

# Contracts
from ml.contracts.identifiers import CANONICAL_VECTOR_DIMENSION, SongId

# Audio pipeline modules
from backend.services.audio_service import (
    TARGET_SAMPLE_RATE,
    N_MFCC,
    AUDIO_EXTS,
    generate_file_hash,
    generate_deterministic_uuid,
    stats7,
    extract_features_for_file
)

# Database Setup
DB_URL = os.environ.get("POSTGRES_URI", "sqlite:///recsys.db")
engine = create_engine(DB_URL)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def process_all_files():
    audio_dir = os.path.join("datasets", "raw", "audio_samples")
    print(f"Scanning for audio files in {audio_dir}...")
    files = []
    for root, _, filenames in os.walk(audio_dir):
        for f in filenames:
            if any(f.lower().endswith(ext) for ext in AUDIO_EXTS):
                files.append(os.path.join(root, f))
    
    print(f"Found {len(files)} files.")
    
    # Process files concurrently using ThreadPoolExecutor for IO/CPU mix
    results = []
    with ProcessPoolExecutor(max_workers=4) as executor:
        for res in executor.map(extract_features_for_file, files):
            results.append(res)
    
    success_results = [r for r in results if r["status"] == "success"]
    error_results = [r for r in results if r["status"] == "error"]
    
    print(f"\nExtraction complete. Success: {len(success_results)}, Errors: {len(error_results)}")
    
    # 4. Qdrant & 5. Database Setup
    from backend.config.settings import settings
    qstore = QdrantVectorStore(collection_name="audio_features", location=settings.QDRANT_URI)
    await qstore.initialize_collection()
    
    db = SessionLocal()
    
    # We need a dummy artist and album to satisfy foreign keys
    dummy_artist_id = uuid.uuid5(uuid.NAMESPACE_OID, "dummy_artist")
    dummy_album_id = uuid.uuid5(uuid.NAMESPACE_OID, "dummy_album")
    
    artist = db.query(Artist).filter_by(id=dummy_artist_id).first()
    if not artist:
        artist = Artist(id=dummy_artist_id, name="Unknown Artist")
        db.add(artist)
    album = db.query(Album).filter_by(id=dummy_album_id).first()
    if not album:
        album = Album(id=dummy_album_id, title="Unknown Album", artist_id=dummy_artist_id)
        db.add(album)
    db.commit()

    qdrant_upsert_count = 0
    db_upsert_count = 0

    for r in success_results:
        sid = r["song_id"]
        # Database
        # Check if song exists
        song = db.query(Song).filter_by(id=sid).first()
        if not song:
            song = Song(
                id=sid,
                title=r["filename"],
                album_id=dummy_album_id,
                artist_id=dummy_artist_id,
                duration_ms=int(r["duration"] * 1000)
            )
            db.add(song)
        
        # Audio feature idempotent insert/update
        af = db.query(AudioFeature).filter_by(song_id=sid).first()
        if not af:
            af = AudioFeature(
                song_id=sid,
                tempo_bpm=r["tempo_bpm"],
                harmonic_ratio=r["harmonic_ratio"],
                vector_dimension=r["feature_dimension"],
                extraction_version=r["extraction_version"]
            )
            db.add(af)
            db_upsert_count += 1
        else:
            if af.extraction_version != r["extraction_version"]:
                af.extraction_version = r["extraction_version"]
                af.tempo_bpm = r["tempo_bpm"]
                af.harmonic_ratio = r["harmonic_ratio"]
                af.vector_dimension = r["feature_dimension"]
                db_upsert_count += 1
        db.commit()

        # Qdrant
        await qstore.upsert(
            song_id=SongId(str(sid)),
            vector=r["vector"],
            payload={
                "song_id": str(sid),
                "filename": r["filename"],
                "file_hash": r["file_hash"],
                "extraction_version": r["extraction_version"],
                "vector_dimension": r["feature_dimension"]
            }
        )
        qdrant_upsert_count += 1

    # 6. Quality Report
    total_time = sum(r["processing_time"] for r in results)
    report_dict = {
        "Total files discovered": len(files),
        "Successful extractions": len(success_results),
        "Failed extractions": len(error_results),
        "Success percentage": (len(success_results)/len(files))*100 if files else 0,
        "Total processing time (s)": total_time,
        "Average processing time (s)": total_time / len(files) if files else 0,
        "Minimum duration (s)": min([r["duration"] for r in success_results]) if success_results else 0,
        "Maximum duration (s)": max([r["duration"] for r in success_results]) if success_results else 0,
        "Qdrant upsert count": qdrant_upsert_count,
        "Database insert/update count": db_upsert_count,
        "Errors": error_results
    }
    
    os.makedirs("datasets/processed", exist_ok=True)
    with open("datasets/processed/audio_ingestion_report.json", "w") as f:
        json.dump(report_dict, f, indent=2)

    os.makedirs("docs", exist_ok=True)
    with open("docs/RealAudioIngestionReport.md", "w") as f:
        f.write("# Real Audio Ingestion Report (Phase 11B)\n\n")
        f.write("## Overview\n")
        for k, v in report_dict.items():
            if k != "Errors":
                f.write(f"- **{k}**: {v}\n")
        
        f.write("\n## Failures\n")
        if not error_results:
            f.write("No failures encountered.\n")
        else:
            for e in error_results:
                f.write(f"- `{e['filename']}`: {e['error_type']} - {e['error_msg']}\n")

    # 8. Verification
    print("\n--- VERIFICATION ---")
    print(f"Total files: {len(files)}")
    print(f"Successful extractions: {len(success_results)}")
    
    q_count = await qstore.client.count(collection_name="audio_features")
    print(f"Qdrant collection count: {q_count.count}")
    
    db_count = db.query(AudioFeature).count()
    print(f"PostgreSQL/SQLite audio_features count: {db_count}")
    
    if q_count.count == len(success_results) and db_count >= len(success_results):
        print("Vector counts agree.")
    else:
        print("WARNING: Vector counts mismatch!")
    
    print("\nRandom Check (up to 5):")
    np.random.seed(42)
    sample_size = min(5, len(success_results))
    if sample_size > 0:
        samples = np.random.choice(success_results, sample_size, replace=False)
        for s in samples:
            sid = str(s["song_id"])
            q_res = await qstore.get(SongId(sid))
            db_res = db.query(AudioFeature).filter_by(song_id=s["song_id"]).first()
            q_ok = len(q_res) == 215 if q_res else False
            db_ok = db_res is not None and db_res.vector_dimension == 215
            print(f"File: {s['filename']} -> SongId: {sid} -> Qdrant OK: {q_ok}, DB OK: {db_ok}")

if __name__ == "__main__":
    asyncio.run(process_all_files())
