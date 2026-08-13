"""
Popularity Recommendation Model
===============================
Implements the RecommendationModelInterface.
"""
import os
import json
import yaml
from datetime import datetime
from typing import Dict, List, Optional

from ml.interfaces.recommendation_model import RecommendationModelInterface
from ml.contracts.models import ModelMetadata, ModelType
from ml.contracts.identifiers import ModelVersion, SongId
from ml.contracts.recommendations import RecommendationRequest, RecommendationResponse, RecommendationScore
from ml.contracts.interactions import InteractionDataset
from ml.popularity.config import PopularityConfig
from ml.popularity.scoring import calculate_decayed_weight
from ml.popularity.normalizer import get_normalizer


class PopularityModel(RecommendationModelInterface):
    """Deterministic Popularity Baseline."""
    
    def __init__(self, config: Optional[PopularityConfig] = None):
        self.config = config or PopularityConfig()
        self.scores: Dict[SongId, float] = {}
        self.metadata: Optional[ModelMetadata] = None
        self._is_ready = False
        self.normalizer = get_normalizer(self.config.normalizer_type)

    async def train(self, dataset: InteractionDataset, **kwargs) -> ModelMetadata:
        """
        Calculates popularity scores from an InteractionDataset.
        Reference time is the end of the dataset's date range.
        """
        reference_time = kwargs.get("reference_time", dataset.date_range_end)
        
        # Aggregate scores
        aggregated: Dict[SongId, float] = {}
        for interaction in dataset.interactions:
            contribution = calculate_decayed_weight(
                interaction=interaction,
                reference_time=reference_time,
                half_life_days=self.config.half_life_days
            )
            aggregated[interaction.song_id] = aggregated.get(interaction.song_id, 0.0) + contribution

        # Sort and store
        sorted_scores = sorted(aggregated.items(), key=lambda x: x[1], reverse=True)
        self.scores = dict(sorted_scores)
        
        # Build raw recommendation scores for normalizer fitting
        raw_scores = []
        for i, (song_id, score) in enumerate(sorted_scores):
            raw_scores.append(RecommendationScore(
                song_id=song_id,
                score=score,
                model_name="popularity",
                model_version=ModelVersion("v1.0.0"),  # Temporary until save
                rank=i+1
            ))
            
        self.normalizer.fit(raw_scores)
        
        # Construct Metadata
        self.metadata = ModelMetadata(
            model_name=f"popularity_{self.config.mode.value}",
            model_type=ModelType.POPULARITY,
            model_version=ModelVersion(kwargs.get("model_version", "v1.0.0")),
            training_timestamp=datetime.utcnow(),
            dataset_version=dataset.dataset_version,
            feature_version="interactions_v1",
            hyperparameters=self.config.model_dump(mode='json'),
            training_parameters={"reference_time": reference_time.isoformat()},
            artifact_path="",
            code_version="latest"
        )
        
        self._is_ready = True
        return self.metadata

    async def predict(self, request: RecommendationRequest) -> RecommendationResponse:
        """Generates recommendations by querying the precomputed scores."""
        if not self._is_ready:
            raise RuntimeError("Model is not trained/loaded.")
            
        exclude_set = set(request.exclude_song_ids)
        
        raw_recommendations = []
        rank = 1
        
        for song_id, score in self.scores.items():
            if song_id in exclude_set:
                continue
                
            rec = RecommendationScore(
                song_id=song_id,
                score=score,
                model_name=self.metadata.model_name,
                model_version=self.metadata.model_version,
                rank=rank
            )
            raw_recommendations.append(rec)
            rank += 1
            
            if len(raw_recommendations) >= request.limit:
                break
                
        # Normalize scores
        normalized_recs = self.normalizer.normalize(raw_recommendations)
        
        return RecommendationResponse(
            user_id=request.user_id,
            recommendations=normalized_recs,
            model_name=self.metadata.model_name,
            model_version=self.metadata.model_version
        )

    async def save(self, artifact_path: str) -> None:
        """Serializes scores.json, config.yaml, and metadata.json."""
        if not self._is_ready:
            raise RuntimeError("Cannot save an untrained model.")
            
        os.makedirs(artifact_path, exist_ok=True)
        
        # 1. scores.json
        with open(os.path.join(artifact_path, "scores.json"), "w") as f:
            json.dump(self.scores, f)
            
        # 2. config.yaml
        with open(os.path.join(artifact_path, "config.yaml"), "w") as f:
            yaml.dump(self.config.model_dump(mode='json'), f)
            
        # 3. metadata.json
        self.metadata.artifact_path = artifact_path
        with open(os.path.join(artifact_path, "metadata.json"), "w") as f:
            f.write(self.metadata.model_dump_json(indent=2))

    async def load(self, artifact_path: str) -> None:
        """Deserializes model artifacts."""
        with open(os.path.join(artifact_path, "scores.json"), "r") as f:
            self.scores = json.load(f)
            
        with open(os.path.join(artifact_path, "config.yaml"), "r") as f:
            config_dict = yaml.safe_load(f)
            self.config = PopularityConfig(**config_dict)
            self.normalizer = get_normalizer(self.config.normalizer_type)
            
        with open(os.path.join(artifact_path, "metadata.json"), "r") as f:
            meta_dict = json.load(f)
            self.metadata = ModelMetadata(**meta_dict)
            
        # Re-fit normalizer for prediction scaling
        raw_scores = [
            RecommendationScore(
                song_id=SongId(song_id), score=score, 
                model_name=self.metadata.model_name, model_version=self.metadata.model_version, rank=i+1
            ) for i, (song_id, score) in enumerate(self.scores.items())
        ]
        self.normalizer.fit(raw_scores)
            
        self._is_ready = True

    def get_metadata(self) -> ModelMetadata:
        if not self._is_ready:
            raise RuntimeError("Model is not loaded.")
        return self.metadata

    def is_ready(self) -> bool:
        return self._is_ready
