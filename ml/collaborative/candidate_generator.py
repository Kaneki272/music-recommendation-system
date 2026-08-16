from typing import List, Tuple, Optional
from ml.collaborative.model import CollaborativeFilteringModel
from ml.contracts.models import ColdStartContext, UserState

class CandidateGenerator:
    """
    Fast candidate generation leveraging implicit's native recommend method.
    Provides cold-start fallbacks.
    """
    def __init__(self, model: CollaborativeFilteringModel, sparse_threshold: int = 5):
        self.cf_model = model
        self.sparse_threshold = sparse_threshold

    def recommend_top_k(
        self, 
        user_id: str, 
        k: int, 
        exclude_song_ids: Optional[List[str]] = None
    ) -> Tuple[List[Tuple[str, float]], ColdStartContext]:
        """
        Returns ( [(song_id, score), ...], ColdStartContext )
        """
        # 1. New User Check
        if user_id not in self.cf_model.dataset_builder.user_mapping:
            return [], ColdStartContext(
                user_id=user_id,
                user_state=UserState.NEW_USER,
                interaction_count=0
            )
            
        internal_user = self.cf_model.dataset_builder.user_mapping[user_id]
        user_row = self.cf_model.user_item_matrix[internal_user]
        interaction_count = user_row.nnz
        
        # 2. Sparse User Check
        if interaction_count < self.sparse_threshold:
            state = UserState.SPARSE_USER
        else:
            state = UserState.RETURNING_USER
            
        context = ColdStartContext(
            user_id=user_id,
            user_state=state,
            interaction_count=interaction_count
        )
        
        # Even sparse users get recommendations from CF, but Hybrid will likely blend Popularity
        
        # 3. Handle exclusions
        filter_items = []
        if exclude_song_ids:
            for s in exclude_song_ids:
                if s in self.cf_model.dataset_builder.song_mapping:
                    filter_items.append(self.cf_model.dataset_builder.song_mapping[s])
                    
        # 4. Implicit Recommend
        # filter_already_liked_items=True automatically filters items present in user_row
        
        n_items = len(self.cf_model.dataset_builder.song_mapping)
        # implicit's recommend adds user_row.nnz to N before calling topk. We must prevent N + nnz > n_items.
        safe_k = min(k, n_items - user_row.nnz - 1)
        if safe_k <= 0:
            return [], context
            
        try:
            item_ids, scores = self.cf_model.model.recommend(
                internal_user, 
                user_row, 
                N=safe_k, 
                filter_already_liked_items=True,
                filter_items=filter_items
            )
        except Exception as e:
            # Fallback if implicit crashes for any bounds reason
            return [], context
        
        # Map back to canonical string IDs
        results = []
        for i, internal_song in enumerate(item_ids):
            song_id = self.cf_model.dataset_builder.reverse_song_mapping[internal_song]
            results.append((song_id, float(scores[i])))
            
        return results, context
