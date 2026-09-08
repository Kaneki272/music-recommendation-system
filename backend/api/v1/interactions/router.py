from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from starlette.concurrency import run_in_threadpool
import uuid
import datetime

from streaming.schemas.events import MusicEvent
from streaming.producers.interaction_producer import InteractionProducer

router = APIRouter(prefix="/interactions", tags=["interactions"])

class InteractionPayload(BaseModel):
    user_id: str
    song_id: str
    interaction_type: str = Field(..., description="E.g., play, like, skip")
    weight: Optional[float] = 1.0

# Singleton producer instance (initialized on startup in main.py ideally, 
# but we can do lazy initialization or dependency injection)
producer_instance = None

def get_producer() -> InteractionProducer:
    global producer_instance
    if producer_instance is None:
        producer_instance = InteractionProducer()
    return producer_instance

@router.post("/")
async def create_interaction(
    payload: InteractionPayload,
    producer: InteractionProducer = Depends(get_producer)
):
    """
    Submit a real interaction event to the Kafka topic.
    The consumer will later persist this to MongoDB.
    """
    event = MusicEvent(
        event_id=str(uuid.uuid4()),
        user_id=payload.user_id,
        track_id=payload.song_id,
        event_type=payload.interaction_type.upper(),
        timestamp=datetime.datetime.utcnow(),
        source="api"
    )
    
    try:
        # Use run_in_threadpool because producer.publish_event is synchronous 
        # and we don't want to block the async FastAPI event loop.
        await run_in_threadpool(producer.publish_event, event)
        return {"status": "success", "event_id": event.event_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to publish event to Kafka: {str(e)}")

