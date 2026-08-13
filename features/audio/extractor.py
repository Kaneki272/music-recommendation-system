"""
Module 5.3 — DSP Feature Extractor
=====================================
The core Librosa wrapper. Extracts three families of acoustic features
from a preprocessed audio signal.

Feature Families:
  A. RHYTHM      — Tempo (BPM), Beat Frames, Onset Strength
  B. TIMBRAL     — MFCCs, Spectral Centroid, Spectral Rolloff,
                   Spectral Bandwidth, Zero Crossing Rate, RMS Energy
  C. HARMONIC    — Chroma STFT, Tonnetz, Harmonic/Percussive separation

Design contract:
  - Input:  ProcessedAudioSignal (from Preprocessor)
  - Output: RawFeatureSet (time-series arrays for each feature)
  - Has zero knowledge of aggregation, storage, or recommendation logic.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass
class RhythmFeatures:
    tempo_bpm: float                        # Global BPM estimate
    beat_frames: np.ndarray                 # Frame indices of beat events
    onset_strength: np.ndarray              # Onset strength envelope


@dataclass
class TimbralFeatures:
    mfcc: np.ndarray                        # Shape: (n_mfcc=20, T)
    spectral_centroid: np.ndarray           # Shape: (1, T)
    spectral_rolloff: np.ndarray            # Shape: (1, T)
    spectral_bandwidth: np.ndarray          # Shape: (1, T)
    zero_crossing_rate: np.ndarray          # Shape: (1, T)
    rms_energy: np.ndarray                  # Shape: (1, T)


@dataclass
class HarmonicFeatures:
    chroma_stft: np.ndarray                 # Shape: (12, T) — 12 pitch classes
    tonnetz: np.ndarray                     # Shape: (6, T) — tonal centroid features
    harmonic_ratio: float                   # Ratio of harmonic to percussive energy


@dataclass
class RawFeatureSet:
    song_id: str
    rhythm: RhythmFeatures
    timbral: TimbralFeatures
    harmonic: HarmonicFeatures
    extraction_duration_ms: float           # Time taken to run extraction


class DSPExtractorInterface(ABC):
    """Abstract base for Librosa DSP extraction."""

    @abstractmethod
    async def extract(self, signal: "ProcessedAudioSignal") -> RawFeatureSet:
        """
        Run all three DSP families on the preprocessed signal.
        Returns raw time-series arrays — NOT aggregated yet.
        """
        pass


class DSPExtractionError(Exception):
    """Raised when DSP extraction fails on the signal."""
    pass
