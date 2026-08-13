"""
Content-Based Strict Temporal Evaluation & Ablation
===================================================
"""
from typing import List, Dict, Set
from datetime import datetime
from collections import defaultdict
import asyncio

from ml.contracts.interactions import InteractionDataset, InteractionType
from ml.contracts.evaluation import EvaluationResult, AccuracyMetrics, BeyondAccuracyMetrics
from ml.contracts.identifiers import SongId, UserId
from ml.content_based.model import ContentBasedModel
from ml.contracts.recommendations import RecommendationRequest

class ContentBasedEvaluator:
    def __init__(self, model: ContentBasedModel, k_values: List[int] = [5, 10, 20]):
        self.model = model
        self.k_values = k_values

    async def evaluate(
        self, 
        training_dataset: InteractionDataset, 
        test_dataset: InteractionDataset
    ) -> EvaluationResult:
        """
        Executes a strict temporal evaluation.
        training_dataset defines the historical interactions (t < T_split).
        test_dataset defines the ground truth (t >= T_split).
        """
        if test_dataset.date_range_start < training_dataset.date_range_end:
            raise ValueError("Data leakage: test dataset overlaps with training dataset.")
            
        user_test_ground_truth: Dict[UserId, Set[SongId]] = defaultdict(set)
        for interaction in test_dataset.interactions:
            if interaction.interaction_type in (InteractionType.PLAY, InteractionType.COMPLETE, InteractionType.LIKE):
                user_test_ground_truth[interaction.user_id].add(interaction.song_id)

        metrics = {k: {"precision": 0.0, "recall": 0.0, "hit_rate": 0.0} for k in self.k_values}
        users_evaluated = 0
        recommended_items = set()
        
        user_train_history: Dict[UserId, Set[SongId]] = defaultdict(set)
        for interaction in training_dataset.interactions:
            user_train_history[interaction.user_id].add(interaction.song_id)

        for user_id, true_items in user_test_ground_truth.items():
            if not true_items:
                continue
                
            request = RecommendationRequest(
                user_id=user_id,
                limit=max(self.k_values),
                exclude_song_ids=list(user_train_history.get(user_id, set()))
            )
            
            response = await self.model.predict(request)
            pred_items = [rec.song_id for rec in response.recommendations]
            
            if not pred_items:
                # Cold start scenario; user dropped
                continue
            
            for k in self.k_values:
                pred_k = pred_items[:k]
                recommended_items.update(pred_k)
                hits = len(set(pred_k) & true_items)
                
                metrics[k]["precision"] += hits / k if k > 0 else 0
                metrics[k]["recall"] += hits / len(true_items)
                metrics[k]["hit_rate"] += 1.0 if hits > 0 else 0.0
                
            users_evaluated += 1

        if users_evaluated == 0:
            raise RuntimeError("No users could be evaluated (perhaps all were cold-start?).")

        accuracy_metrics = []
        for k in self.k_values:
            accuracy_metrics.append(AccuracyMetrics(
                k=k,
                precision_at_k=metrics[k]["precision"] / users_evaluated,
                recall_at_k=metrics[k]["recall"] / users_evaluated,
                hit_rate_at_k=metrics[k]["hit_rate"] / users_evaluated
            ))
            
        beyond = BeyondAccuracyMetrics(
            coverage=len(recommended_items) / 1000.0  # Placeholder catalog size
        )
        
        return EvaluationResult(
            model_name=self.model.get_metadata().model_name,
            model_version=self.model.get_metadata().model_version,
            dataset_version=test_dataset.dataset_version,
            k_values=self.k_values,
            accuracy_metrics=accuracy_metrics,
            beyond_accuracy=beyond,
            evaluation_set_size=users_evaluated
        )

# -- Ablation Definition Helper --
def create_ablation_configs():
    from ml.content_based.config import ContentBasedConfig, SimilarityWeights
    
    return {
        "A_audio_only": ContentBasedConfig(
            similarity_weights=SimilarityWeights(audio_weight=1.0, genre_weight=0.0, artist_weight=0.0)
        ),
        "B_audio_genre": ContentBasedConfig(
            similarity_weights=SimilarityWeights(audio_weight=0.7, genre_weight=0.3, artist_weight=0.0)
        ),
        "C_audio_metadata": ContentBasedConfig(
            similarity_weights=SimilarityWeights(audio_weight=0.5, genre_weight=0.3, artist_weight=0.2)
        )
    }
