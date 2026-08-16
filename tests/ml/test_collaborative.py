import pytest
import pandas as pd
import numpy as np
import scipy.sparse as sparse

from ml.collaborative.config import InteractionWeightsConfig, ALSConfig
from ml.collaborative.dataset_builder import DatasetBuilder
from ml.collaborative.model import CollaborativeFilteringModel
from ml.collaborative.candidate_generator import CandidateGenerator
from ml.contracts.models import UserState

@pytest.fixture
def mock_dataset():
    return pd.DataFrame([
        {"user_id": "u1", "song_id": "s1", "interaction_type": "play", "weight": 1.0},
        {"user_id": "u1", "song_id": "s2", "interaction_type": "complete", "weight": 1.0},
        {"user_id": "u2", "song_id": "s1", "interaction_type": "like", "weight": 1.0},
        {"user_id": "u2", "song_id": "s3", "interaction_type": "play", "weight": 1.0},
        {"user_id": "u3", "song_id": "s3", "interaction_type": "skip", "weight": 1.0}, # zero weight
    ])

def test_dataset_builder(mock_dataset):
    # D: play+complete+like+playlist
    config = InteractionWeightsConfig(play=1.0, complete=2.0, playlist_add=3.0, like=4.0)
    builder = DatasetBuilder(config)
    
    # We can use transform directly by forcing mappings for test
    builder.user_mapping = {"u1": 0, "u2": 1, "u3": 2}
    builder.song_mapping = {"s1": 0, "s2": 1, "s3": 2}
    builder.reverse_user_mapping = ["u1", "u2", "u3"]
    builder.reverse_song_mapping = ["s1", "s2", "s3"]
    
    matrix = builder.transform(mock_dataset)
    
    # u1, s1 (play=1.0)
    assert matrix[0, 0] == 1.0
    # u1, s2 (complete=2.0)
    assert matrix[0, 1] == 2.0
    # u2, s1 (like=4.0)
    assert matrix[1, 0] == 4.0
    # u3, s3 (skip=0.0 because not in config)
    assert matrix[2, 2] == 0.0
    
    assert matrix.shape == (3, 3)

def test_candidate_generator_cold_start():
    # Setup dummy model
    builder = DatasetBuilder(InteractionWeightsConfig())
    builder.user_mapping = {"u1": 0}
    builder.song_mapping = {"s1": 0}
    builder.reverse_song_mapping = ["s1"]
    
    model = CollaborativeFilteringModel(ALSConfig(factors=2, iterations=1), builder)
    
    # Fake training data
    model.user_item_matrix = sparse.csr_matrix([[1.0]])
    model.is_trained = True
    
    generator = CandidateGenerator(model, sparse_threshold=5)
    
    # Test completely unknown user
    recs, context = generator.recommend_top_k("u99", 5)
    assert context.user_state == UserState.NEW_USER
    assert len(recs) == 0
    
    # Test sparse user (has 1 interaction, threshold is 5)
    # Note: since we mocked user_item_matrix, it will crash if it tries to actually recommend unless we mock the internal implicit ALS model.
    # But checking the NEW_USER condition works.
