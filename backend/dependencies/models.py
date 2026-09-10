import os
from fastapi import HTTPException
from ml.collaborative.model import CollaborativeFilteringModel
from ml.collaborative.candidate_generator import CandidateGenerator
from ml.popularity.model import PopularityModel
from ml.content_based.model import ContentBasedModel
from ml.hybrid.engine import HybridRecommendationEngine
from feature_store.feast_provider import FeastFeatureProvider
from backend.database.qdrant.client import QdrantVectorStore

_hybrid_engine = None

async def get_hybrid_engine() -> HybridRecommendationEngine:
    global _hybrid_engine
    if _hybrid_engine is not None:
        return _hybrid_engine

    try:
        als_path = "models/collaborative/v1"
        pop_path = "models/popularity/v1"
        content_path = "models/content/v1"

        if not os.path.exists(als_path) or not os.path.exists(os.path.join(als_path, "model.pkl")):
            raise FileNotFoundError(f"ALS model not found in {als_path}")
        if not os.path.exists(pop_path) or not os.path.exists(os.path.join(pop_path, "scores.json")):
            raise FileNotFoundError(f"Popularity model not found in {pop_path}")
        if not os.path.exists(content_path) or not os.path.exists(os.path.join(content_path, "metadata.json")):
            raise FileNotFoundError(f"Content model not found in {content_path}")

        als = CollaborativeFilteringModel.load(als_path)
        generator = CandidateGenerator(model=als)
        
        pop = PopularityModel()
        await pop.load(pop_path)
        
        vector_store = QdrantVectorStore()
        feature_provider = FeastFeatureProvider(repo_path="feature_store/repo", qdrant_store=vector_store)
        
        content = ContentBasedModel(feature_provider=feature_provider, vector_store=vector_store)
        await content.load(content_path)
        
        _hybrid_engine = HybridRecommendationEngine(
            als_model=generator,
            popularity_model=pop,
            content_model=content,
            content_available=True
        )
        return _hybrid_engine
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Recommendation Engine not initialized: {e}")
