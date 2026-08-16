"""
Content-Based Recommendation Model
==================================
Implements RecommendationModelInterface.
Fuses Qdrant Vector Search with Metadata boosting.

Cold-start / sparse-profile semantics:
  COLD_START     — model returns empty list; metadata field `profile_state = COLD_START`
  SPARSE_PROFILE — model returns degraded recommendations; metadata field marks degraded state
  NORMAL         — full recommendation pass
"""
import os
import json
import yaml
from datetime import datetime
from typing import Dict, List, Optional

from ml.interfaces.recommendation_model import RecommendationModelInterface
from ml.interfaces.feature_provider import FeatureProviderInterface
from ml.interfaces.embedding_provider import VectorStoreInterface
from ml.contracts.models import ModelMetadata, ModelType
from ml.contracts.identifiers import ModelVersion, SongId
from ml.contracts.recommendations import RecommendationRequest, RecommendationResponse, RecommendationScore
from ml.contracts.interactions import InteractionDataset
from ml.content_based.config import ContentBasedConfig
from ml.content_based.profiler import UserTasteProfiler, ProfileState
from ml.content_based.similarity import calculate_metadata_boost


class ContentBasedModel(RecommendationModelInterface):
    def __init__(
        self,
        feature_provider: FeatureProviderInterface,
        vector_store: VectorStoreInterface,
        config: Optional[ContentBasedConfig] = None
    ):
        self.config = config or ContentBasedConfig()
        self.feature_provider = feature_provider
        self.vector_store = vector_store
        self.metadata: Optional[ModelMetadata] = None
        self._is_ready = False
        self.profiler = UserTasteProfiler(
            half_life_days=self.config.profiler_half_life_days,
            minimum_interaction_threshold=self.config.minimum_interaction_threshold
        )
        # Historical interaction dataset for inference-time profiling
        self.historical_dataset: Optional[InteractionDataset] = None

    async def train(self, dataset: InteractionDataset, **kwargs) -> ModelMetadata:
        """
        'Training' in Content-Based v1 stores the historical dataset for inference-time
        profiling and persists the config. Qdrant is pre-populated by the ETL layer.
        """
        self.historical_dataset = dataset
        reference_time = kwargs.get("reference_time", dataset.date_range_end)

        self.metadata = ModelMetadata(
            model_name="content_based",
            model_type=ModelType.CONTENT_BASED,
            model_version=ModelVersion(kwargs.get("model_version", "v1.0.0")),
            training_timestamp=datetime.utcnow(),
            dataset_version=dataset.dataset_version,
            feature_version="audio_v1",
            hyperparameters=self.config.model_dump(mode='json'),
            training_parameters={"reference_time": reference_time.isoformat()},
            artifact_path="",
            code_version="latest"
        )
        self._is_ready = True
        return self.metadata

    async def predict(self, request: RecommendationRequest) -> RecommendationResponse:
        """
        Generates recommendations by profiling the user and querying Qdrant.

        Returns an explicit `profile_state` in the response metadata:
          - COLD_START     → empty recommendations list
          - SPARSE_PROFILE → degraded list with warning in metadata
          - NORMAL         → full list
        """
        if not self._is_ready:
            raise RuntimeError("Model is not loaded or trained.")

        # 1. Fetch User Representation from Feature Store
        user_rep = await self.feature_provider.get_user_representation(request.user_id)

        # Hard cold-start: no user record at all
        if not user_rep or user_rep.is_new_user:
            return RecommendationResponse(
                user_id=request.user_id,
                recommendations=[],
                model_name=self.metadata.model_name,
                model_version=self.metadata.model_version,
                metadata={"profile_state": ProfileState.COLD_START.value}
            )

        # 2. Gather user's historical interactions (strictly before reference_time)
        ref_time = datetime.fromisoformat(self.metadata.training_parameters["reference_time"])
        user_interactions = [
            i for i in self.historical_dataset.interactions
            if i.user_id == request.user_id and i.timestamp < ref_time
        ]

        # Fetch audio features for interacted songs
        interacted_song_ids = list(set(i.song_id for i in user_interactions))
        audio_features = await self.feature_provider.batch_get_audio_features(interacted_song_ids)

        # 3. Generate Taste Profile — receives explicit ProfileResult with state
        profile_result = self.profiler.generate_profile(user_interactions, audio_features, ref_time)

        if profile_result.state == ProfileState.COLD_START:
            return RecommendationResponse(
                user_id=request.user_id,
                recommendations=[],
                model_name=self.metadata.model_name,
                model_version=self.metadata.model_version,
                metadata={"profile_state": ProfileState.COLD_START.value}
            )

        # For SPARSE_PROFILE, we still generate recommendations but mark the state.
        # The Hybrid Engine can use `profile_state` to weight this model's output lower.
        profile_state_label = profile_result.state.value

        # 4. Qdrant Retrieval — use larger pool to survive filtering
        pool_size = request.limit * self.config.retrieval_candidate_pool_multiplier
        qdrant_results = await self.vector_store.search(
            query_vector=profile_result.vector, top_k=pool_size
        )

        # 5. Metadata Boosting & Exclusion Filtering
        exclude_set = set(request.exclude_song_ids)
        scored_candidates = []

        for q_res in qdrant_results:
            if q_res.song_id in exclude_set:
                continue

            content_rep = await self.feature_provider.get_content_representation(q_res.song_id)
            meta_features = content_rep.metadata_features if content_rep else None

            meta_boost = calculate_metadata_boost(
                user_genres=user_rep.favorite_genres,
                user_artists=[],
                candidate_metadata=meta_features,
                genre_weight=self.config.similarity_weights.genre_weight,
                artist_weight=self.config.similarity_weights.artist_weight
            )

            # Score: audio cosine similarity (weighted) + metadata boost
            audio_score = q_res.score * self.config.similarity_weights.audio_weight
            final_score = audio_score + meta_boost

            scored_candidates.append({"song_id": q_res.song_id, "score": final_score})

        # 6. Rank and Format
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)

        final_recs = [
            RecommendationScore(
                song_id=cand["song_id"],
                score=cand["score"],
                model_name=self.metadata.model_name,
                model_version=self.metadata.model_version,
                rank=rank + 1,
                metadata={"profile_state": profile_state_label}
            )
            for rank, cand in enumerate(scored_candidates[:request.limit])
        ]

        return RecommendationResponse(
            user_id=request.user_id,
            recommendations=final_recs,
            model_name=self.metadata.model_name,
            model_version=self.metadata.model_version,
            metadata={
                "profile_state": profile_state_label,
                "valid_interactions": profile_result.valid_interaction_count,
                "total_profile_weight": profile_result.total_weight
            }
        )

    async def save(self, artifact_path: str) -> None:
        if not self._is_ready:
            raise RuntimeError("Cannot save an untrained model.")

        os.makedirs(artifact_path, exist_ok=True)

        with open(os.path.join(artifact_path, "config.yaml"), "w") as f:
            yaml.dump(self.config.model_dump(mode='json'), f)

        self.metadata.artifact_path = artifact_path
        with open(os.path.join(artifact_path, "metadata.json"), "w") as f:
            f.write(self.metadata.model_dump_json(indent=2))

    async def load(self, artifact_path: str) -> None:
        with open(os.path.join(artifact_path, "config.yaml"), "r") as f:
            config_dict = yaml.safe_load(f)
            self.config = ContentBasedConfig(**config_dict)
            self.profiler = UserTasteProfiler(
                half_life_days=self.config.profiler_half_life_days,
                minimum_interaction_threshold=self.config.minimum_interaction_threshold
            )

        with open(os.path.join(artifact_path, "metadata.json"), "r") as f:
            meta_dict = json.load(f)
            self.metadata = ModelMetadata(**meta_dict)

        self._is_ready = True

    def get_metadata(self) -> ModelMetadata:
        if not self._is_ready:
            raise RuntimeError("Model is not loaded.")
        return self.metadata

    def is_ready(self) -> bool:
        return self._is_ready
