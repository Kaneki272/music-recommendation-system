import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from ml.interfaces.recommendation_model import RecommendationModelInterface

class Evaluator:
    """
    Common Evaluation Harness for Recommendation Models.
    Computes Precision@K, Recall@K, NDCG@K, HitRate@K, Coverage, and Diversity.
    """
    def __init__(self, k_values: List[int] = [5, 10]):
        self.k_values = k_values

    def evaluate(self, model: RecommendationModelInterface, train_df: pd.DataFrame, eval_df: pd.DataFrame) -> Dict[str, float]:
        """
        Evaluates the given model on the eval_df (which could be validation or test).
        Uses train_df to exclude already interacted items.
        """
        # Group eval data by user
        eval_users = eval_df.groupby('user_id')['song_id'].apply(set).to_dict()
        train_users = train_df.groupby('user_id')['song_id'].apply(set).to_dict()
        
        # We need the candidate generator or predict function. 
        # For simplicity, we assume the model has a recommend_top_k or we just use predict on all catalog
        # Wait, the contract says RecommendationModelInterface has predict(user, songs).
        # We should use a CandidateGenerator if available for speed, but let's assume predict is fast enough
        # Actually, for CF, predict on all songs is slow. Let's see if the model has recommend_top_k.
        
        metrics = {f"Precision@{k}": [] for k in self.k_values}
        metrics.update({f"Recall@{k}": [] for k in self.k_values})
        metrics.update({f"NDCG@{k}": [] for k in self.k_values})
        metrics.update({f"HitRate@{k}": [] for k in self.k_values})
        
        all_recommended_songs = set()
        recommended_lists_for_diversity = []
        total_users = 0
        
        # We need a catalog of all possible songs to recommend
        catalog = list(set(train_df['song_id'].unique()).union(set(eval_df['song_id'].unique())))
        
        for user_id, true_items in eval_users.items():
            if not true_items:
                continue
                
            total_users += 1
            exclude_items = train_users.get(user_id, set())
            
            # Use recommend_top_k if it exists (like CandidateGenerator), else fallback
            if hasattr(model, 'recommend_top_k'):
                # model here is a CandidateGenerator wrapper
                recs, _ = model.recommend_top_k(user_id, max(self.k_values), exclude_song_ids=list(exclude_items))
                top_items = [song_id for song_id, score in recs]
            else:
                # predict on all catalog
                candidates = [s for s in catalog if s not in exclude_items]
                scores = model.predict(user_id, candidates)
                top_items = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:max(self.k_values)]
                
            for k in self.k_values:
                k_items = top_items[:k]
                hits = len(set(k_items).intersection(true_items))
                
                metrics[f"Precision@{k}"].append(hits / k if k > 0 else 0)
                metrics[f"Recall@{k}"].append(hits / len(true_items))
                metrics[f"HitRate@{k}"].append(1.0 if hits > 0 else 0.0)
                
                # NDCG
                dcg = sum(1.0 / np.log2(i + 2) for i, item in enumerate(k_items) if item in true_items)
                idcg = sum(1.0 / np.log2(i + 2) for i in range(min(len(true_items), k)))
                ndcg = dcg / idcg if idcg > 0 else 0.0
                metrics[f"NDCG@{k}"].append(ndcg)
                
            if len(top_items) > 0:
                # coverage tracks top-K max
                all_recommended_songs.update(top_items)
                recommended_lists_for_diversity.append(top_items)
                
        # Aggregate
        result = {}
        for k in metrics:
            result[k] = np.mean(metrics[k]) if metrics[k] else 0.0
            
        result["Coverage"] = len(all_recommended_songs) / len(catalog) if catalog else 0.0
        
        # Diversity: Recommendation-set diversity (Personalization)
        # Measured as 1 - average pairwise Jaccard similarity between users' top-K lists.
        # We use a randomized sample of pairs if the user count is large to avoid O(N^2).
        
        all_lists = [set(top_items) for top_items in recommended_lists_for_diversity if len(top_items) > 0]
        if len(all_lists) > 1:
            # Sample up to 1000 random pairs to estimate diversity efficiently
            import random
            num_pairs = min(1000, len(all_lists) * (len(all_lists) - 1) // 2)
            similarities = []
            
            for _ in range(num_pairs):
                i, j = random.sample(range(len(all_lists)), 2)
                set1, set2 = all_lists[i], all_lists[j]
                intersection = len(set1.intersection(set2))
                union = len(set1.union(set2))
                jaccard = intersection / union if union > 0 else 0.0
                similarities.append(jaccard)
                
            avg_similarity = sum(similarities) / len(similarities)
            result["Diversity"] = 1.0 - avg_similarity
        else:
            result["Diversity"] = 0.0
        
        return result
