"""
Popularity Evaluation Baseline
==============================
Evaluates the popularity model using a strict temporal split.
"""
from typing import List, Dict, Set
from datetime import datetime
from collections import defaultdict

from ml.contracts.interactions import InteractionDataset, InteractionType
from ml.contracts.evaluation import EvaluationResult, AccuracyMetrics, BeyondAccuracyMetrics
from ml.contracts.identifiers import SongId, UserId
from ml.popularity.model import PopularityModel
from ml.contracts.recommendations import RecommendationRequest

class TemporalEvaluator:
    def __init__(self, model: PopularityModel, k_values: List[int] = [5, 10, 20]):
        self.model = model
        self.k_values = k_values

    async def evaluate(
        self, 
        training_dataset: InteractionDataset, 
        test_dataset: InteractionDataset
    ) -> EvaluationResult:
        """
        Executes a temporal evaluation. 
        The model MUST have been trained ONLY on training_dataset.
        test_dataset contains future interactions to predict.
        """
        if test_dataset.date_range_start < training_dataset.date_range_end:
            raise ValueError("Data leakage: test dataset overlaps with training dataset.")
            
        # Group test interactions by user
        user_test_ground_truth: Dict[UserId, Set[SongId]] = defaultdict(set)
        for interaction in test_dataset.interactions:
            if interaction.interaction_type in (InteractionType.PLAY, InteractionType.COMPLETE, InteractionType.LIKE):
                user_test_ground_truth[interaction.user_id].add(interaction.song_id)
                
        if not user_test_ground_truth:
            raise ValueError("Test dataset contains no positive interactions.")

        metrics = {k: {"precision": 0.0, "recall": 0.0, "hit_rate": 0.0} for k in self.k_values}
        users_evaluated = 0
        recommended_items = set()

        # Popularity is non-personalized, so we only need to predict once for cold-start evaluation,
        # but to simulate a real scenario where a user might have excluded history, 
        # we predict per user excluding their past history.
        
        # Build user training history for exclusions
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
            
            for k in self.k_values:
                pred_k = pred_items[:k]
                recommended_items.update(pred_k)
                hits = len(set(pred_k) & true_items)
                
                metrics[k]["precision"] += hits / k if k > 0 else 0
                metrics[k]["recall"] += hits / len(true_items)
                metrics[k]["hit_rate"] += 1.0 if hits > 0 else 0.0
                
            users_evaluated += 1

        # Aggregate Metrics
        accuracy_metrics = []
        for k in self.k_values:
            accuracy_metrics.append(AccuracyMetrics(
                k=k,
                precision_at_k=metrics[k]["precision"] / users_evaluated,
                recall_at_k=metrics[k]["recall"] / users_evaluated,
                hit_rate_at_k=metrics[k]["hit_rate"] / users_evaluated
            ))
            
        beyond = BeyondAccuracyMetrics(
            coverage=len(recommended_items) / max(1, len(self.model.scores))
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
