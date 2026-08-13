"""
Module 5.1 — Audio Fetcher
===========================
Responsible ONLY for retrieving raw audio data from a source URI.
Supports multiple backend sources: HTTP URL (Spotify preview), local
filesystem, or a cloud storage URI (S3-compatible).

Design contract:
  - Input:  A source URI string
  - Output: Raw audio bytes written to a temporary local path
  - Has zero knowledge of DSP, Librosa, or any database.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class AudioSourceType(str, Enum):
    HTTP_URL = "http_url"          # Spotify 30s preview URLs or CDN links
    LOCAL_FILE = "local_file"      # Raw audio already on disk
    S3_URI = "s3_uri"              # Cloud object storage (future)


@dataclass
class AudioSource:
    uri: str
    source_type: AudioSourceType
    song_id: str                   # Internal UUID for correlation


@dataclass
class FetchedAudio:
    song_id: str
    local_path: str                # Temp path to the downloaded file
    source_type: AudioSourceType
    file_size_bytes: int


class AudioFetcherInterface(ABC):
    """Abstract base for all audio retrieval backends."""

    @abstractmethod
    async def fetch(self, source: AudioSource) -> FetchedAudio:
        """
        Retrieve audio from the given source and write it to a temp
        local path. Raises AudioFetchError on failure.
        """
        pass

    @abstractmethod
    async def cleanup(self, fetched: FetchedAudio) -> None:
        """Delete the local temp file after processing is complete."""
        pass


class AudioFetchError(Exception):
    """Raised when audio cannot be retrieved from the source."""
    pass
