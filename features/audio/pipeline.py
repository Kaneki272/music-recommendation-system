"""
Audio Extraction Pipeline Orchestrator
========================================
Ties modules 5.1 → 5.2 → 5.3 → 5.4 together into a single
callable pipeline. This is the ONLY entry point for audio
feature extraction across the entire system.

Flow:
  1. Fetch audio from source URI             (AudioFetcherInterface)
  2. Preprocess to standard signal           (AudioPreprocessorInterface)
  3. Extract raw DSP features                (DSPExtractorInterface)
  4. Aggregate into fixed-length vector      (FeatureAggregatorInterface)
  5. Persist to PostgreSQL + sync to Qdrant  (downstream consumers)

Design:
  - Each step is injected via constructor (testable, swappable)
  - Failures at any step are caught and logged to ExtractionJobTracker
  - Pipeline is stateless — safe to run concurrently across workers
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from features.audio.schema import AudioFeatureCreate, ExtractionJobStatus
from features.audio.fetcher import AudioSource


@dataclass
class PipelineResult:
    song_id: str
    success: bool
    feature: Optional[AudioFeatureCreate] = None
    error: Optional[str] = None


class AudioExtractionPipeline(ABC):
    """Abstract orchestrator interface for the extraction pipeline."""

    @abstractmethod
    async def run(self, source: AudioSource, job_id: str) -> PipelineResult:
        """
        Execute the full Fetch → Preprocess → Extract → Aggregate pipeline
        for a single song. Returns a PipelineResult indicating success or failure.
        """
        pass

    @abstractmethod
    async def run_batch(
        self,
        sources: list[AudioSource],
        job_id: str,
        concurrency: int = 4
    ) -> list[PipelineResult]:
        """
        Process multiple songs concurrently. Respects the concurrency
        limit to avoid saturating the CPU during DSP computation.
        """
        pass
