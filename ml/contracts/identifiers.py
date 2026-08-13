"""
ML Contract — Canonical Identifiers
======================================
SINGLE SOURCE OF TRUTH for all entity identifiers used across
PostgreSQL, MongoDB, Qdrant, the Feature Store, and every ML model.

RULES (mandatory — violating these breaks cross-system compatibility):
  1. `song_id`        — The canonical ML identifier for a track.
                        Always an internal UUID from the `songs` table.
  2. `user_id`        — The canonical ML identifier for a user.
                        Always an internal UUID from the `users` table.
  3. `spotify_track_id` — EXTERNAL identifier. Only used in the ETL layer.
                        ML models MUST NOT use spotify_track_id as a key.
  4. All IDs are Python `str` wrapping UUIDs (no raw uuid.UUID objects in ML code).
  5. IDs MUST be consistent across every store:
       PostgreSQL → MongoDB → Qdrant → Feature Store → Model Artifacts

ANTI-PATTERNS (forbidden):
  - Using spotify_track_id as a Qdrant point ID
  - Using artist name strings as keys in interaction matrices
  - Using auto-incremented integers as ML identifiers
"""
from typing import NewType

# ── Canonical Internal Identifiers ────────────────────────────
SongId     = NewType("SongId",     str)  # Internal UUID — PRIMARY ML KEY for tracks
UserId     = NewType("UserId",     str)  # Internal UUID — PRIMARY ML KEY for users
ArtistId   = NewType("ArtistId",   str)  # Internal UUID
AlbumId    = NewType("AlbumId",    str)  # Internal UUID
PlaylistId = NewType("PlaylistId", str)  # Internal UUID
SessionId  = NewType("SessionId",  str)  # Ephemeral session UUID

# ── External Identifiers (ETL layer only) ─────────────────────
SpotifyTrackId  = NewType("SpotifyTrackId",  str)  # e.g., "4cOdK2wGLETKBW3PvgPWqT"
SpotifyArtistId = NewType("SpotifyArtistId", str)
SpotifyAlbumId  = NewType("SpotifyAlbumId",  str)

# ── Model/Job Identifiers ─────────────────────────────────────
ModelVersion    = NewType("ModelVersion",    str)  # e.g., "v1.2.0"
DatasetVersion  = NewType("DatasetVersion",  str)  # e.g., "2026-08-01"
JobId           = NewType("JobId",           str)  # UUID for ETL/training jobs

CANONICAL_VECTOR_DIMENSION: int = 222  # The fixed dimension of audio_feature_vector
