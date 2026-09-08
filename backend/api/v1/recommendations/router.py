from fastapi import APIRouter, Depends, Query, HTTPException
from ml.contracts.recommendations import RecommendationRequest, RecommendationResponse
from ml.hybrid.engine import HybridRecommendationEngine
from backend.dependencies.models import get_hybrid_engine

from backend.dependencies.database import get_mongo_db
from backend.repositories.interaction import InteractionRepository

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

@router.get("/", response_model=RecommendationResponse)
async def get_recommendations(
    user_id: str,
    limit: int = Query(10, ge=1, le=50),
    engine: HybridRecommendationEngine = Depends(get_hybrid_engine),
    mongo_db = Depends(get_mongo_db)
):
    req = RecommendationRequest(
        user_id=user_id,
        limit=limit,
        exclude_song_ids=[]
    )
    try:
        # Wire the real user interaction history
        interaction_repo = InteractionRepository(mongo_db["user_interactions"])
        count = await interaction_repo.get_interaction_count(user_id)
        
        # Inject the real count so the engine's get_user_state knows about it
        engine.user_interaction_counts[user_id] = count
        
        response = await engine.predict(req)
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
