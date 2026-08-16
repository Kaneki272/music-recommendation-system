import os
import json
import pickle
from implicit.als import AlternatingLeastSquares
from scipy import sparse

from ml.contracts.models import ModelMetadata, ModelVersion, DatasetVersion
from ml.interfaces.recommendation_model import RecommendationModelInterface
from ml.collaborative.config import ALSConfig
from ml.collaborative.dataset_builder import DatasetBuilder

class CollaborativeFilteringModel(RecommendationModelInterface):
    """
    Implicit ALS Baseline Collaborative Filtering Model.
    """
    def __init__(self, config: ALSConfig, dataset_builder: DatasetBuilder):
        self.config = config
        self.dataset_builder = dataset_builder
        self.model = AlternatingLeastSquares(**self.config.to_dict())
        self.is_trained = False
        
        # User-item matrix stored for candidate generation (user historical exclusions)
        self.user_item_matrix: sparse.csr_matrix = None 

    def train(self, user_item_matrix: sparse.csr_matrix):
        """
        Trains the implicit ALS model.
        In implicit version >= 0.6.0, fit() expects a user x item matrix!
        
        Confidence = 1 + alpha * matrix
        """
        self.user_item_matrix = user_item_matrix
        
        # Apply alpha confidence scaling
        confidence_matrix = (user_item_matrix * self.config.alpha).astype('double')
        
        # implicit >= 0.6.0 fit requires user_item matrix
        self.model.fit(confidence_matrix)
        self.is_trained = True

    def predict(self, user_id: str, song_ids: list[str]) -> dict[str, float]:
        """
        Predict scores for a specific user and list of songs.
        """
        if not self.is_trained:
            raise ValueError("Model is not trained.")
            
        if user_id not in self.dataset_builder.user_mapping:
            return {s: 0.0 for s in song_ids}
            
        internal_user = self.dataset_builder.user_mapping[user_id]
        
        scores = {}
        # Fetch the user factors
        user_factors = self.model.user_factors[internal_user]
        
        for song_id in song_ids:
            if song_id not in self.dataset_builder.song_mapping:
                scores[song_id] = 0.0
            else:
                internal_song = self.dataset_builder.song_mapping[song_id]
                song_factors = self.model.item_factors[internal_song]
                # Implicit ALS score is dot product
                score = user_factors.dot(song_factors)
                scores[song_id] = float(score)
                
        return scores

    def save(self, path: str):
        """Saves model weights and mappings."""
        os.makedirs(path, exist_ok=True)
        
        # Save mappings
        with open(os.path.join(path, "user_mapping.json"), "w") as f:
            json.dump(self.dataset_builder.user_mapping, f)
            
        with open(os.path.join(path, "song_mapping.json"), "w") as f:
            json.dump(self.dataset_builder.song_mapping, f)
            
        # Save implicit model
        with open(os.path.join(path, "model.pkl"), "wb") as f:
            pickle.dump(self.model, f)
            
        # Save historical user_item_matrix
        sparse.save_npz(os.path.join(path, "user_item_matrix.npz"), self.user_item_matrix)

    @classmethod
    def load(cls, path: str, config: ALSConfig = None) -> 'CollaborativeFilteringModel':
        """Loads model weights and mappings."""
        if config is None:
            config = ALSConfig() # In real implementation, read from config.yaml
            
        # Mappings
        with open(os.path.join(path, "user_mapping.json"), "r") as f:
            user_mapping = json.load(f)
            
        with open(os.path.join(path, "song_mapping.json"), "r") as f:
            song_mapping = json.load(f)
            
        # DatasetBuilder
        builder = DatasetBuilder(weight_config=None) # Weights only needed for training
        builder.user_mapping = user_mapping
        builder.song_mapping = song_mapping
        builder.reverse_user_mapping = [k for k, v in sorted(user_mapping.items(), key=lambda item: item[1])]
        builder.reverse_song_mapping = [k for k, v in sorted(song_mapping.items(), key=lambda item: item[1])]
        
        # Instantiate
        instance = cls(config, builder)
        
        # Load implicit model
        with open(os.path.join(path, "model.pkl"), "rb") as f:
            instance.model = pickle.load(f)
            
        instance.user_item_matrix = sparse.load_npz(os.path.join(path, "user_item_matrix.npz"))
        instance.is_trained = True
        return instance

    def get_metadata(self) -> ModelMetadata:
        # In a real setup, we would read the metadata.json saved during train/save.
        # Here we just mock it for interface compliance.
        return ModelMetadata(
            model_name="CollaborativeFiltering_ALS",
            model_type="collaborative",
            model_version="v1.0.0",
            training_timestamp="2026-08-16T12:00:00Z",
            dataset_version="v1.0.0",
            feature_version="none",
            artifact_path="models/collaborative/v1",
            code_version="unknown"
        )
        
    def is_ready(self) -> bool:
        return self.is_trained
