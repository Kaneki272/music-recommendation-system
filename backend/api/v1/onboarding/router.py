from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from typing import List
from backend.dependencies.database import get_mongo_db, get_postgres_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.models.song import Song

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

class OnboardingPreferences(BaseModel):
    user_id: str
    selected_genres: List[str] = []
    selected_artist_ids: List[str] = []
    selected_song_ids: List[str] = []

@router.get("/options")
async def get_onboarding_options(postgres_db: AsyncSession = Depends(get_postgres_db)):
    """
    Returns a curated list of genres and popular artists/songs for the user to select from.
    """
    # For now, we can return some hardcoded popular genres
    genres = ["Pop", "Rock", "Hip-Hop", "Jazz", "Classical", "Electronic", "R&B", "Country"]
    
    # We can fetch a few random or popular artists/songs from Postgres if needed, 
    # but for simplicity, returning empty lists or a small sample.
    return {
        "genres": genres,
        "artists": [],
        "songs": []
    }

@router.post("/preferences")
async def save_onboarding_preferences(
    preferences: OnboardingPreferences = Body(...),
    mongo_db = Depends(get_mongo_db)
):
    """
    Saves the user's selected preferences to MongoDB.
    This resolves the cold start by providing initial features for the Content-Based model.
    """
    try:
        collection = mongo_db["user_preferences"]
        
        # Upsert user preferences
        await collection.update_one(
            {"user_id": preferences.user_id},
            {"$set": preferences.dict()},
            upsert=True
        )
        
        # TODO: Trigger a Feast sync job here if needed asynchronously
        
        return {"status": "success", "message": "Preferences saved successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
