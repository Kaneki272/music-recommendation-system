"""
Module 5.2 — Audio Preprocessor
=================================
Standardizes raw audio so every extraction algorithm receives
a consistent baseline signal. Must run before any DSP.

Pipeline:
  1. Decode any format (MP3, FLAC, WAV, OGG) → PCM float32
  2. Convert stereo/multi-channel → mono (average channels)
  3. Resample to TARGET_SAMPLE_RATE (22,050 Hz)
  4. Trim leading and trailing silence (top_db=30)

Design contract:
  - Input:  Local audio file path (from AudioFetcher)
  - Output: ProcessedAudioSignal (numpy array + metadata)
  - No knowledge of features, Kafka, or databases.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

# Standard sample rate for music analysis (Librosa default)
TARGET_SAMPLE_RATE: int = 22_050


@dataclass
class ProcessedAudioSignal:
    song_id: str
    signal: np.ndarray          # Mono PCM float32 array
    sample_rate: int            # Always TARGET_SAMPLE_RATE after preprocessing
    duration_seconds: float
    original_format: str        # e.g., "mp3", "flac"


class AudioPreprocessorInterface(ABC):
    """Abstract base for audio standardization."""

    @abstractmethod
    async def preprocess(self, song_id: str, local_path: str) -> ProcessedAudioSignal:
        """
        Load, decode, convert to mono, resample, and trim silence.
        Returns a ProcessedAudioSignal ready for feature extraction.
        """
        pass


class AudioPreprocessError(Exception):
    """Raised when audio cannot be decoded or standardized."""
    pass
