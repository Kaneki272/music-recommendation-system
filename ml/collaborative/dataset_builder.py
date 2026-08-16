import pandas as pd
import numpy as np
from scipy import sparse
from typing import Tuple, Dict, List
import pyarrow.parquet as pq

from ml.collaborative.config import InteractionWeightsConfig

class DatasetBuilder:
    """
    Builds the sparse user-item interaction matrix required by Implicit ALS.
    Strictly prevents temporal leakage by mapping only observed training entities.
    """
    def __init__(self, weight_config: InteractionWeightsConfig):
        self.weight_config = weight_config
        self.user_mapping: Dict[str, int] = {}
        self.song_mapping: Dict[str, int] = {}
        self.reverse_user_mapping: List[str] = []
        self.reverse_song_mapping: List[str] = []

    def fit_transform(self, parquet_path: str) -> sparse.csr_matrix:
        """
        Reads training data, builds the mappings, and constructs the user-item matrix.
        Returns the User-Item matrix (scipy.sparse.csr_matrix).
        """
        table = pq.read_table(parquet_path)
        df = table.to_pandas()
        
        # 1. Build Mappings
        unique_users = df['user_id'].unique()
        unique_songs = df['song_id'].unique()
        
        self.reverse_user_mapping = unique_users.tolist()
        self.user_mapping = {u: i for i, u in enumerate(self.reverse_user_mapping)}
        
        self.reverse_song_mapping = unique_songs.tolist()
        self.song_mapping = {s: i for i, s in enumerate(self.reverse_song_mapping)}
        
        # 2. Map IDs to internal indices
        user_indices = df['user_id'].map(self.user_mapping).values
        song_indices = df['song_id'].map(self.song_mapping).values
        
        # 3. Apply weights
        weights = df['interaction_type'].apply(self.weight_config.get_weight).values
        
        # Multiply by explicit weight if available in the dataset schema (e.g. repeated plays)
        if 'weight' in df.columns:
            weights = weights * df['weight'].values
            
        # 4. Construct Sparse Matrix
        # shape: (users, items)
        user_item_matrix = sparse.csr_matrix(
            (weights, (user_indices, song_indices)),
            shape=(len(self.user_mapping), len(self.song_mapping))
        )
        
        # Note: sparse.csr_matrix sums up duplicate entries automatically when building!
        # This is perfect for implicit feedback (e.g., 3 plays = weight * 3).
        
        return user_item_matrix
        
    def transform(self, df: pd.DataFrame) -> sparse.csr_matrix:
        """
        Constructs a matrix for new data using existing mappings.
        Ignores unknown users or songs.
        """
        valid_df = df[
            df['user_id'].isin(self.user_mapping) & 
            df['song_id'].isin(self.song_mapping)
        ].copy()
        
        if valid_df.empty:
            return sparse.csr_matrix((len(self.user_mapping), len(self.song_mapping)))
            
        user_indices = valid_df['user_id'].map(self.user_mapping).values
        song_indices = valid_df['song_id'].map(self.song_mapping).values
        weights = valid_df['interaction_type'].apply(self.weight_config.get_weight).values
        if 'weight' in valid_df.columns:
            weights = weights * valid_df['weight'].values
            
        return sparse.csr_matrix(
            (weights, (user_indices, song_indices)),
            shape=(len(self.user_mapping), len(self.song_mapping))
        )
