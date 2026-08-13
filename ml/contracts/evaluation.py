"""
ML Contract — Evaluation Result
==================================
Standardized structure for recording offline evaluation results.
Every model evaluation run MUST produce an EvaluationResult.

Metrics defined here (implementations deferred to Phase 13):
  Accuracy:     Precision@K, Recall@K, MAP@K, NDCG@K, HitRate@K
  Beyond:       Coverage, Diversity, Novelty, Serendipity

The K values (e.g., K=5, K=10, K=20) are configurable per experiment.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime

from ml.contracts.identifiers import ModelVersion, DatasetVersion


class AccuracyMetrics(BaseModel):
    """Relevance accuracy metrics at cut-off K."""
    k: int = Field(..., description="The cut-off rank K")
    precision_at_k: Optional[float] = None
    recall_at_k: Optional[float] = None
    map_at_k: Optional[float] = None
    ndcg_at_k: Optional[float] = None
    hit_rate_at_k: Optional[float] = None


class BeyondAccuracyMetrics(BaseModel):
    """
    Beyond-accuracy metrics measuring recommendation quality
    beyond pure relevance — critical for a music discovery system.
    """
    coverage: Optional[float] = Field(
        None, description="Fraction of catalog the system can recommend (0.0–1.0)"
    )
    diversity: Optional[float] = Field(
        None, description="Average pairwise dissimilarity within a recommendation list"
    )
    novelty: Optional[float] = Field(
        None, description="Average popularity of recommended items (lower = more novel)"
    )
    serendipity: Optional[float] = Field(
        None, description="Fraction of useful, unexpected recommendations"
    )


class EvaluationResult(BaseModel):
    """
    Complete evaluation record for a model version against a test dataset.
    Stored alongside ModelMetadata in the model artifact directory.
    """
    model_name: str
    model_version: ModelVersion
    dataset_version: DatasetVersion
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
    k_values: List[int] = Field(default_factory=lambda: [5, 10, 20])
    accuracy_metrics: List[AccuracyMetrics] = Field(default_factory=list)
    beyond_accuracy: Optional[BeyondAccuracyMetrics] = None
    evaluation_set_size: int = Field(..., description="Number of users evaluated")
    notes: Optional[str] = None
