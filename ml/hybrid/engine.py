from typing import List, Dict, Any, Optional
from datetime import datetime

from ml.interfaces.recommendation_model import RecommendationModelInterface
from ml.contracts.recommendations import RecommendationRequest, RecommendationResponse, RecommendationScore
from ml.contracts.models import ModelMetadata

from ml.hybrid.config import HybridConfig
from ml.hybrid.scorer import ScoreNormalizer, HybridScorer
from ml.hybrid.filters import HardFilter, PostProcessor


class HybridRecommendationEngine(RecommendationModelInterface):
    """
    Orchestrates candidate generation, filtering, score normalization, 
    and hybrid scoring.
    """
    
    def __init__(self, als_model=None, popularity_model=None, content_model=None, 
                 user_interaction_counts: Dict[str, int] = None,
                 song_to_artist_map: Dict[str, str] = None,
                 als_min: float = -1.0, als_max: float = 2.0, max_pop: float = 10000.0,
                 content_available: bool = False):
        
        self.als_model = als_model
        self.popularity_model = popularity_model
        self.content_model = content_model
        
        self.user_interaction_counts = user_interaction_counts or {}
        self.song_to_artist_map = song_to_artist_map or {}
        
        self.normalizer = ScoreNormalizer(als_min=als_min, als_max=als_max, max_pop=max_pop)
        self.scorer = HybridScorer()
        
        self.content_available = content_available
        self._ready = True

    async def train(self, dataset_version: str, **kwargs) -> ModelMetadata:
        # Hybrid engine doesn't train its own weights yet, it orchestrates pre-trained models.
        return self.get_metadata()

    def get_user_state(self, user_id: str) -> str:
        interactions = self.user_interaction_counts.get(user_id, 0)
        if interactions == HybridConfig.NEW_USER_THRESHOLD:
            return "NEW_USER"
        elif interactions <= HybridConfig.SPARSE_USER_MAX:
            return "SPARSE_USER"
        else:
            return "KNOWN_USER"

    async def predict(self, request: RecommendationRequest) -> RecommendationResponse:
        # 1. User State Detection
        interactions = self.user_interaction_counts.get(request.user_id, 0)
        user_state = self.get_user_state(request.user_id)
        
        # Determine base weights based on state and content availability
        base_weights = HybridConfig.get_base_weights(interactions, self.content_available)
        
        available_models = []
        
        # 2. Candidate Generation (Synchronous ML inference wrapped in async boundary conceptually)
        candidates_als, candidates_pop, candidates_content = {}, {}, {}
        
        if self.popularity_model and base_weights.get("popularity", 0) > 0:
            # Extract top items from the precomputed sorted scores
            recs = []
            for s, sc in self.popularity_model.scores.items():
                recs.append((s, float(sc)))
                if len(recs) >= request.limit * 5:
                    break
            candidates_pop = dict(recs)
            available_models.append("popularity")
            
        if self.als_model and base_weights.get("als", 0) > 0:
            try:
                # Use collaborative recommend_top_k
                recs, _ = self.als_model.recommend_top_k(request.user_id, request.limit * 5)
                candidates_als = dict(recs)
                available_models.append("als")
            except Exception:
                # Unknown user to ALS
                pass
                
        if self.content_model and self.content_available and base_weights.get("content", 0) > 0:
            try:
                recs, _ = self.content_model.recommend_top_k(request.user_id, request.limit * 5)
                candidates_content = dict(recs)
                available_models.append("content")
            except Exception:
                pass

        # Renormalize weights among actually successful models (e.g., if ALS failed for unknown user)
        active_weights = self.scorer.renormalize_weights(base_weights, available_models)

        # Candidate Union (Deduplication via Set)
        union_candidates = set(candidates_als.keys()) | set(candidates_pop.keys()) | set(candidates_content.keys())
        
        # 3. Hard Filtering
        filtered_candidates = HardFilter.apply(
            candidates=list(union_candidates),
            exclude_song_ids=request.exclude_song_ids,
            recently_played_song_ids=request.recently_played_song_ids,
            blocked_song_ids=request.blocked_song_ids,
            blocked_artist_ids=request.blocked_artist_ids,
            song_to_artist_map=self.song_to_artist_map
        )
        
        # 4. Hybrid Scoring & Normalization
        scored_results = []
        for song_id in filtered_candidates:
            c_als = candidates_als.get(song_id, None)
            c_pop = candidates_pop.get(song_id, None)
            c_content = candidates_content.get(song_id, None)
            
            # If a model didn't return this candidate but we have its fallback predict method, we could query it.
            # But predicting every missing item might be slow. For now, treat missing as None and score handles it (scores 0 for that component).
            
            score_data = self.scorer.score(
                als_raw=c_als,
                pop_raw=c_pop,
                content_raw=c_content,
                weights=active_weights,
                normalizer=self.normalizer
            )
            
            scored_results.append({
                "song_id": song_id,
                "final_score": score_data["final_score"],
                "contributions": score_data["contributions"],
                "sources": {
                    "als_raw": c_als,
                    "pop_raw": c_pop,
                    "content_raw": c_content
                }
            })
            
        # Sort by final score
        scored_results.sort(key=lambda x: x["final_score"], reverse=True)
        
        # 5. Post-Processing
        post_processed = PostProcessor.apply_artist_limit(
            scored_recommendations=scored_results,
            song_to_artist_map=self.song_to_artist_map,
            limit=HybridConfig.ARTIST_REPETITION_LIMIT
        )
        
        # Limit to request
        final_top_k = post_processed[:request.limit]
        
        # Format output
        recommendations = []
        for rank, rec in enumerate(final_top_k, 1):
            recommendations.append(RecommendationScore(
                song_id=rec["song_id"],
                score=rec["final_score"],
                model_name="hybrid",
                model_version="v1.0.0",
                rank=rank,
                metadata={
                    "user_state": user_state,
                    "contributions": rec["contributions"]
                }
            ))
            
        return RecommendationResponse(
            user_id=request.user_id,
            recommendations=recommendations,
            model_name="hybrid",
            model_version="v1.0.0",
            metadata={
                "user_state": user_state,
                "active_weights": active_weights
            }
        )

    async def save(self, artifact_path: str) -> None:
        pass

    async def load(self, artifact_path: str) -> None:
        pass

    def get_metadata(self) -> ModelMetadata:
        return ModelMetadata(
            model_name="hybrid",
            model_version="v1.0.0",
            dataset_version="hybrid",
            created_at=datetime.utcnow()
        )

    def is_ready(self) -> bool:
        return self._ready
