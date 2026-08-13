"""
Content-Based Recommendation Model
==================================
Implements RecommendationModelInterface.
Fuses Qdrant Vector Search with Metadata boosting.
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
from ml.content_based.profiler import UserTasteProfiler
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
        self.profiler = UserTasteProfiler(self.config.profiler_half_life_days)
        # We also need a historical interaction dataset for prediction profiling
        self.historical_dataset: Optional[InteractionDataset] = None

    async def train(self, dataset: InteractionDataset, **kwargs) -> ModelMetadata:
        """
        'Training' in Content-Based v1 is storing the historical dataset for inference profiling
        and persisting the configuration. Qdrant is already populated by the ETL layer.
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
        """Generates recommendations by profiling the user and querying Qdrant."""
        if not self._is_ready:
            raise RuntimeError("Model is not loaded.")
            
        # 1. Fetch User Profile
        user_rep = await self.feature_provider.get_user_representation(request.user_id)
        
        # Cold start handling - if new user, Content-Based returns empty.
        if not user_rep or user_rep.is_new_user:
            return RecommendationResponse(
                user_id=request.user_id,
                recommendations=[],
                model_name=self.metadata.model_name,
                model_version=self.metadata.model_version
            )
            
        # 2. Get User's Interactions to build taste vector
        # (Filter interactions belonging to this user)
        user_interactions = [i for i in self.historical_dataset.interactions if i.user_id == request.user_id]
        
        # Fetch audio features for those interacted songs
        interacted_song_ids = list(set(i.song_id for i in user_interactions))
        audio_features = await self.feature_provider.batch_get_audio_features(interacted_song_ids)
        
        # 3. Generate Taste Vector
        # Use current time as reference to apply decay relative to now, 
        # but in strict evaluation we use the training reference_time.
        ref_time = datetime.fromisoformat(self.metadata.training_parameters["reference_time"])
        taste_vector = self.profiler.generate_profile(user_interactions, audio_features, ref_time)
        
        if not taste_vector:
            # Fallback if profile generation failed
            return RecommendationResponse(
                user_id=request.user_id, recommendations=[], 
                model_name=self.metadata.model_name, model_version=self.metadata.model_version
            )
            
        # 4. Qdrant Retrieval
        pool_size = request.limit * self.config.retrieval_candidate_pool_multiplier
        qdrant_results = await self.vector_store.search(query_vector=taste_vector, top_k=pool_size)
        
        # 5. Metadata Boosting & Filtering
        exclude_set = set(request.exclude_song_ids)
        scored_candidates = []
        
        for q_res in qdrant_results:
            if q_res.song_id in exclude_set:
                continue
                
            # Fetch structured metadata via Feast adapter
            content_rep = await self.feature_provider.get_content_representation(q_res.song_id)
            meta_features = content_rep.metadata_features if content_rep else None
            
            meta_boost = calculate_metadata_boost(
                user_genres=user_rep.favorite_genres,
                user_artists=[], # Not implemented in v1 schema
                candidate_metadata=meta_features,
                genre_weight=self.config.similarity_weights.genre_weight,
                artist_weight=self.config.similarity_weights.artist_weight
            )
            
            # Final Score Fusion
            # Raw cosine similarity is preserved exactly as Qdrant semantics output it, plus metadata
            audio_score = q_res.score * self.config.similarity_weights.audio_weight
            final_score = audio_score + meta_boost
            
            scored_candidates.append({
                "song_id": q_res.song_id,
                "score": final_score
            })
            
        # 6. Rank and Format
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        final_recs = []
        
        for rank, cand in enumerate(scored_candidates[:request.limit]):
            final_recs.append(RecommendationScore(
                song_id=cand["song_id"],
                score=cand["score"],
                model_name=self.metadata.model_name,
                model_version=self.metadata.model_version,
                rank=rank + 1
            ))
            
        return RecommendationResponse(
            user_id=request.user_id,
            recommendations=final_recs,
            model_name=self.metadata.model_name,
            model_version=self.metadata.model_version
        )

    async def save(self, artifact_path: str) -> None:
        if not self._is_ready:
            raise RuntimeError("Cannot save an untrained model.")
        
        os.makedirs(artifact_path, exist_ok=True)
        
        # Save config
        with open(os.path.join(artifact_path, "config.yaml"), "w") as f:
            yaml.dump(self.config.model_dump(mode='json'), f)
            
        # Save metadata
        self.metadata.artifact_path = artifact_path
        with open(os.path.join(artifact_path, "metadata.json"), "w") as f:
            f.write(self.metadata.model_dump_json(indent=2))
            
        # In a real system, the dataset wouldn't be pickled whole, but referenced by dataset_version
        # We simulate this by trusting the loader gets the right dataset later.
        
    async def load(self, artifact_path: str) -> None:
        with open(os.path.join(artifact_path, "config.yaml"), "r") as f:
            config_dict = yaml.safe_load(f)
            self.config = ContentBasedConfig(**config_dict)
            self.profiler = UserTasteProfiler(self.config.profiler_half_life_days)
            
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
