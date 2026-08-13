"""
PostgreSQL persistence model for extracted audio features.
Each row corresponds to one song's complete acoustic fingerprint.
The vector itself is synced to Qdrant; this table acts as the
source-of-truth and audit log for what was extracted and when.
"""
import uuid
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from backend.models.base import Base


class AudioFeature(Base):
    __tablename__ = "audio_features"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    song_id = Column(UUID(as_uuid=True), ForeignKey("songs.id"), unique=True, nullable=False, index=True)

    # Stored separately for fast SQL filtering (e.g., "find songs with BPM 120-130")
    tempo_bpm = Column(Float, nullable=False)
    harmonic_ratio = Column(Float, nullable=False)
    vector_dimension = Column(Integer, nullable=False)

    # Versioning for controlled reprocessing
    extraction_version = Column(String(20), nullable=False)
    is_valid = Column(Boolean, default=True)

    extracted_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))
