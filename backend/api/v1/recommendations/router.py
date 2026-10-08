from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
import json
import uuid

from ml.contracts.recommendations import RecommendationRequest, RecommendationResponse, RecommendationScore
from ml.hybrid.engine import HybridRecommendationEngine
from backend.dependencies.models import get_hybrid_engine
from backend.dependencies.database import get_mongo_db, get_postgres_db, get_redis_client
from backend.repositories.interaction import InteractionRepository
from backend.models.song import Song

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

@router.get("/", response_model=RecommendationResponse)
async def get_recommendations(
    user_id: str,
    limit: int = Query(10, ge=1, le=50),
    engine: HybridRecommendationEngine = Depends(get_hybrid_engine),
    mongo_db = Depends(get_mongo_db),
    postgres_db: AsyncSession = Depends(get_postgres_db),
    redis_client = Depends(get_redis_client)
):
    req = RecommendationRequest(
        user_id=user_id,
        limit=limit,
        exclude_song_ids=[]
    )
    try:
        # Cache key based on user and limit
        cache_key = f"recs:user:{user_id}:limit:{limit}"
        
        if redis_client:
            cached_res = await redis_client.get(cache_key)
            if cached_res:
                import logging
                logging.getLogger("recsys.metrics").info(f"Cache Hit | key={cache_key}")
                data = json.loads(cached_res)
                # Reconstruct Pydantic models from dict
                items = [RecommendationScore(**item) for item in data["recommendations"]]
                return RecommendationResponse(recommendations=items)
            
        import logging
        logging.getLogger("recsys.metrics").info(f"Cache Miss | key={cache_key}")
        
        # Wire the real user interaction history
        interaction_repo = InteractionRepository(mongo_db["user_interactions"])
        count = await interaction_repo.get_interaction_count(user_id)
        
        # Inject the real count so the engine's get_user_state knows about it
        engine.user_interaction_counts[user_id] = count
        
        response = await engine.predict(req)
        
        # Batch Postgres Metadata Hydration
        song_ids = [uuid.UUID(rec.song_id) for rec in response.recommendations]
        if song_ids and postgres_db:
            stmt = select(Song).options(joinedload(Song.artist), joinedload(Song.album)).filter(Song.id.in_(song_ids))
            result = await postgres_db.execute(stmt)
            songs = result.scalars().all()
            
            # Map by string ID for quick lookup
            song_map = {str(song.id): song for song in songs}
            
            # Enrich recommendations with audio stream URLs and metadata
            for rec in response.recommendations:
                if rec.metadata is None:
                    rec.metadata = {}
                song = song_map.get(rec.song_id)
                if song:
                    rec.metadata["title"] = song.title
                    rec.metadata["artist"] = song.artist.name if song.artist else "Unknown Artist"
                    if song.album and getattr(song.album, "cover_image_url", None):
                        rec.metadata["cover_image_url"] = song.album.cover_image_url
                rec.metadata["audio_url"] = f"/api/v1/songs/{rec.song_id}/stream"
                
        # Set cache with TTL of 5 minutes
        if redis_client:
            # Pydantic v1 vs v2 dict output handle
            resp_dict = {"recommendations": [item.dict() for item in response.recommendations]}
            await redis_client.setex(cache_key, 300, json.dumps(resp_dict))
            
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
