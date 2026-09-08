# FastAPI Application Entry Point
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from kafka.admin import KafkaAdminClient

from backend.dependencies.database import (
    init_postgres, close_postgres, get_postgres_db,
    init_mongo, close_mongo, get_mongo_db,
    init_redis, close_redis, get_redis_client
)
from backend.config.settings import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Initializing databases...")
    await init_postgres()
    await init_mongo()
    await init_redis()
    yield
    # Shutdown
    print("Closing databases...")
    await close_postgres()
    await close_mongo()
    await close_redis()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title='Hybrid Music Recommendation Engine',
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from backend.api.v1.recommendations.router import router as recommendations_router
from backend.api.v1.interactions.router import router as interactions_router

app.include_router(recommendations_router, prefix="/api/v1")
app.include_router(interactions_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    """General application status"""
    return {"status": "ok", "app": "Music Recommendation API"}

@app.get("/health/db")
async def health_db(
    pg_session: AsyncSession = Depends(get_postgres_db),
    mongo_db = Depends(get_mongo_db)
):
    """Verify PostgreSQL and MongoDB connections"""
    status = {"postgres": "unhealthy", "mongodb": "unhealthy"}
    
    # Check Postgres
    try:
        await pg_session.execute(text("SELECT 1"))
        status["postgres"] = "ok"
    except Exception as e:
        status["postgres"] = f"error: {str(e)}"
        
    # Check MongoDB
    try:
        await mongo_db.command("ping")
        status["mongodb"] = "ok"
    except Exception as e:
        status["mongodb"] = f"error: {str(e)}"
        
    if "error" in status["postgres"] or "error" in status["mongodb"]:
        raise HTTPException(status_code=503, detail=status)
        
    return status

@app.get("/health/streaming")
async def health_streaming(
    redis_client = Depends(get_redis_client)
):
    """Verify Redis and Kafka connections"""
    status = {"redis": "unhealthy", "kafka": "unhealthy"}
    
    # Check Redis
    try:
        await redis_client.ping()
        status["redis"] = "ok"
    except Exception as e:
        status["redis"] = f"error: {str(e)}"
        
    # Check Kafka metadata (blocking call wrapped safely if possible, but admin client is synchronous)
    try:
        import asyncio
        def _check_kafka():
            client = KafkaAdminClient(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","),
                request_timeout_ms=2000
            )
            client.list_topics()
            client.close()
            
        await asyncio.to_thread(_check_kafka)
        status["kafka"] = "ok"
    except Exception as e:
        status["kafka"] = f"error: {str(e)}"
        
    if "error" in status["redis"] or "error" in status["kafka"]:
        raise HTTPException(status_code=503, detail=status)
        
    return status
