"""
ML Contract — Content Feature Representation
===============================================
Defines the multi-modal content representation consumed by the
Content-Based Filtering engine (Phase 8).

Architecture principle: MISSING MODALITIES ARE ALLOWED.
  Song A: audio + metadata + lyrics    → all 3 modalities present
  Song B: audio + metadata             → text_embedding is None
  Song C: metadata only                → audio_features is None

The Content-Based model MUST handle None modalities gracefully.
It MUST NOT crash because one modality is unavailable.

DO NOT confuse:
  AudioFeatureVector  → raw 222-dim acoustic features (this contract)
  ContentEmbedding    → the learned dense representation (Phase 8 output)
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from ml.contracts.identifiers import SongId, ArtistId, AlbumId
from ml.contracts.audio import AudioFeatureVector


class MetadataFeatureVector(BaseModel):
    """
    Structured metadata features about a song.
    Consumed alongside AudioFeatureVector by the Content engine.
    """
    song_id: SongId
    duration_ms: int
    explicit: bool = False
    release_year: Optional[int] = None
    genres: List[str] = Field(default_factory=list)
    language: Optional[str] = None
    market_count: Optional[int] = None          # How many regional markets it's available in
    artist_popularity: Optional[float] = None   # Spotify artist popularity [0, 100]
    album_track_count: Optional[int] = None


class TextEmbedding(BaseModel):
    """
    Dense embedding from text content (lyrics, description).
    The embedding model name and dimension are recorded for compatibility checks.
    """
    song_id: SongId
    embedding_vector: List[float]
    embedding_dimension: int
    embedding_model: str = Field(..., description="e.g., 'sentence-transformers/all-MiniLM-L6-v2'")
    source: str = Field(..., description="lyrics | description | artist_bio")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ContentRepresentation(BaseModel):
    """
    Unified multi-modal content representation for a single song.

    ALL fields are Optional. The consuming model MUST handle every
    combination of present and missing modalities.

    This is the input contract for the Content-Based Filtering engine.
    """
    song_id: SongId

    # ── Modalities (all optional) ───────────────────────────────
    audio_features: Optional[AudioFeatureVector] = Field(
        None, description="222-dim acoustic feature vector from Phase 5 pipeline"
    )
    metadata_features: Optional[MetadataFeatureVector] = Field(
        None, description="Structured song metadata"
    )
    text_embedding: Optional[TextEmbedding] = Field(
        None, description="Dense lyrics/description embedding"
    )

    @property
    def available_modalities(self) -> List[str]:
        """Returns a list of which modalities are present for this song."""
        modalities = []
        if self.audio_features is not None:
            modalities.append("audio")
        if self.metadata_features is not None:
            modalities.append("metadata")
        if self.text_embedding is not None:
            modalities.append("text")
        return modalities

    @property
    def has_minimum_modality(self) -> bool:
        """A song must have at least ONE modality to be recommendable."""
        return len(self.available_modalities) > 0
