"""
Tests for all ML Contracts — Phase 5.5
=========================================
Tests the contracts and interfaces, NOT algorithm implementations.
"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from ml.contracts.identifiers import (
    SongId, UserId, CANONICAL_VECTOR_DIMENSION
)
from ml.contracts.audio import AudioFeatureVector
from ml.contracts.content import ContentRepresentation, MetadataFeatureVector
from ml.contracts.user import UserRepresentation
from ml.contracts.interactions import (
    InteractionRecord, InteractionType, InteractionWeightConfig, InteractionDataset
)
from ml.contracts.recommendations import RecommendationScore, RecommendationRequest
from ml.contracts.candidates import CandidateSong, CandidateSet, SourceScore
from ml.contracts.models import ModelMetadata, ModelType, ColdStartContext, UserState
from ml.contracts.datasets import DatasetMetadata
from ml.contracts.evaluation import EvaluationResult, AccuracyMetrics


# ── Fixtures ────────────────────────────────────────────────────

VALID_SONG_ID = SongId("550e8400-e29b-41d4-a716-446655440000")
VALID_USER_ID = UserId("660e8400-e29b-41d4-a716-446655440001")
VALID_VECTOR = [float(i) for i in range(CANONICAL_VECTOR_DIMENSION)]


# ── 1. Identifier Tests ─────────────────────────────────────────

def test_canonical_vector_dimension_is_222():
    assert CANONICAL_VECTOR_DIMENSION == 222


def test_song_id_is_str():
    song_id = SongId("some-uuid")
    assert isinstance(song_id, str)


def test_user_id_is_str():
    user_id = UserId("some-uuid")
    assert isinstance(user_id, str)


# ── 2. Audio Feature Contract Tests ────────────────────────────

def test_audio_feature_vector_valid():
    afv = AudioFeatureVector(
        song_id=VALID_SONG_ID,
        audio_feature_vector=VALID_VECTOR,
        feature_dimension=222,
        extraction_version="v1.0.0",
        preprocessing_version="v1.0.0",
    )
    assert afv.feature_dimension == 222
    assert len(afv.audio_feature_vector) == 222


def test_audio_feature_vector_rejects_wrong_dimension():
    with pytest.raises(ValidationError):
        AudioFeatureVector(
            song_id=VALID_SONG_ID,
            audio_feature_vector=[0.1] * 100,   # Wrong dimension
            feature_dimension=100,
            extraction_version="v1.0.0",
            preprocessing_version="v1.0.0",
        )


def test_audio_feature_vector_rejects_mismatched_length():
    with pytest.raises(ValidationError):
        AudioFeatureVector(
            song_id=VALID_SONG_ID,
            audio_feature_vector=[0.1] * 50,    # Doesn't match 222
            feature_dimension=222,              # Claims 222 but vector is 50
            extraction_version="v1.0.0",
            preprocessing_version="v1.0.0",
        )


# ── 3. Content Representation Tests ────────────────────────────

def test_content_representation_all_modalities_none():
    """A song with no modalities is still a valid ContentRepresentation."""
    cr = ContentRepresentation(song_id=VALID_SONG_ID)
    assert cr.audio_features is None
    assert cr.metadata_features is None
    assert cr.text_embedding is None
    assert cr.available_modalities == []
    assert cr.has_minimum_modality is False


def test_content_representation_partial_modalities():
    """Audio only — text missing — should not crash."""
    from ml.contracts.audio import AudioFeatureVector
    afv = AudioFeatureVector(
        song_id=VALID_SONG_ID,
        audio_feature_vector=VALID_VECTOR,
        feature_dimension=222,
        extraction_version="v1.0.0",
        preprocessing_version="v1.0.0",
    )
    cr = ContentRepresentation(song_id=VALID_SONG_ID, audio_features=afv)
    assert "audio" in cr.available_modalities
    assert "text" not in cr.available_modalities
    assert cr.has_minimum_modality is True


# ── 4. User Representation Tests ───────────────────────────────

def test_new_user_detection():
    user = UserRepresentation(user_id=VALID_USER_ID)
    assert user.is_new_user is True


def test_returning_user_detection():
    user = UserRepresentation(
        user_id=VALID_USER_ID,
        listening_history_count=50,
    )
    assert user.is_new_user is False


# ── 5. Interaction Record Tests ────────────────────────────────

def test_valid_interaction_record():
    record = InteractionRecord(
        user_id=VALID_USER_ID,
        song_id=VALID_SONG_ID,
        interaction_type=InteractionType.LIKE,
        timestamp=datetime.utcnow(),
        weight=4.0,
    )
    assert record.weight == 4.0


def test_interaction_weight_config():
    config = InteractionWeightConfig()
    assert config.get_weight(InteractionType.LIKE) == 4.0
    assert config.get_weight(InteractionType.SKIP) == -1.0
    assert config.get_weight(InteractionType.COMPLETE) == 2.0


# ── 6. Recommendation Output Tests ─────────────────────────────

def test_recommendation_score_valid():
    score = RecommendationScore(
        song_id=VALID_SONG_ID,
        score=0.87,
        model_name="content_based",
        model_version="v1",
        rank=1,
    )
    assert score.rank == 1
    assert score.score == 0.87


def test_recommendation_score_rank_must_be_positive():
    with pytest.raises(ValidationError):
        RecommendationScore(
            song_id=VALID_SONG_ID,
            score=0.5,
            model_name="popularity",
            model_version="v1",
            rank=0,     # rank must be ≥ 1
        )


# ── 7. Candidate Set Tests ──────────────────────────────────────

def test_candidate_multi_source():
    candidate = CandidateSong(
        song_id=VALID_SONG_ID,
        source_scores={
            "content_based": SourceScore(
                model_name="content_based", model_version="v1",
                raw_score=0.82, normalized_score=0.74
            ),
            "collaborative": SourceScore(
                model_name="collaborative", model_version="v1",
                raw_score=0.71, normalized_score=0.68
            ),
        }
    )
    assert candidate.is_multi_source is True
    assert "content_based" in candidate.source_model_names


def test_candidate_set_lookup():
    candidate = CandidateSong(
        song_id=VALID_SONG_ID,
        source_scores={
            "popularity": SourceScore(
                model_name="popularity", model_version="v1", raw_score=0.93
            )
        }
    )
    cs = CandidateSet(
        user_id=VALID_USER_ID,
        candidates=[candidate],
        source_models=["popularity"]
    )
    found = cs.get_candidate(VALID_SONG_ID)
    assert found is not None
    assert found.song_id == VALID_SONG_ID


# ── 8. Model Metadata Tests ────────────────────────────────────

def test_model_metadata_valid():
    meta = ModelMetadata(
        model_name="content_based_v1",
        model_type=ModelType.CONTENT_BASED,
        model_version="v1.0.0",
        training_timestamp=datetime.utcnow(),
        dataset_version="2026-08-01",
        feature_version="audio_v1.0.0",
        artifact_path="models/content_based/v1/",
        code_version="85dc3e2",
    )
    assert meta.is_production is False


# ── 9. Cold Start Tests ─────────────────────────────────────────

def test_new_user_requires_popularity_fallback():
    ctx = ColdStartContext(
        user_id=VALID_USER_ID,
        user_state=UserState.NEW_USER,
        interaction_count=0,
    )
    assert ctx.requires_popularity_fallback() is True
    assert ctx.allows_collaborative() is False


def test_returning_user_allows_collaborative():
    ctx = ColdStartContext(
        user_id=VALID_USER_ID,
        user_state=UserState.RETURNING_USER,
        interaction_count=250,
    )
    assert ctx.requires_popularity_fallback() is False
    assert ctx.allows_collaborative() is True


# ── 10. Dataset Metadata Tests ──────────────────────────────────

def test_dataset_metadata_valid():
    meta = DatasetMetadata(
        dataset_name="interaction_dataset",
        dataset_version="2026-08-01",
        source="mongodb.listening_history",
        row_count=1_000_000,
        feature_version="audio_v1.0.0",
        preprocessing_version="preprocessor_v1.0.0",
    )
    assert meta.row_count == 1_000_000


# ── 11. Evaluation Result Tests ──────────────────────────────────

def test_evaluation_result_valid():
    result = EvaluationResult(
        model_name="content_based",
        model_version="v1.0.0",
        dataset_version="2026-08-01",
        k_values=[5, 10, 20],
        accuracy_metrics=[
            AccuracyMetrics(k=10, precision_at_k=0.31, ndcg_at_k=0.42)
        ],
        evaluation_set_size=500,
    )
    assert result.accuracy_metrics[0].k == 10
