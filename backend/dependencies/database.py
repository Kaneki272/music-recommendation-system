"""
Database dependency injection and connection management.
"""
from typing import AsyncGenerator, Optional
import motor.motor_asyncio
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.config.settings import settings

# Global connection pools
postgres_engine = None
postgres_session_factory = None
mongo_client = None
redis_client = None

# Ensure all models are imported so they register with Base.metadata
from backend.models.base import Base
import backend.models.user
import backend.models.rbac
import backend.models.artist
import backend.models.album
import backend.models.song
import backend.models.audio_features
import backend.models.playlist
import backend.models.playlist_song
import backend.models.refresh_token
import backend.models.etl_tracking

import logging
logger = logging.getLogger("recsys.db")

async def init_postgres():
    global postgres_engine, postgres_session_factory
    postgres_engine = create_async_engine(
        settings.POSTGRES_URI,
        echo=False,
        future=True,
    )
    postgres_session_factory = sessionmaker(
        postgres_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    table_count = len(Base.metadata.tables)
    logger.info(f"Loaded {table_count} SQLAlchemy tables.")
    if table_count == 0:
        logger.error("No tables were loaded! The imports may have failed.")
    
    logger.info(f"Initializing PostgreSQL schema on {settings.POSTGRES_HOST}...")
    try:
        # Use engine.begin() which commits automatically
        async with postgres_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("PostgreSQL schema initialization completed successfully.")
    except Exception as e:
        import traceback
        logger.error(f"Schema initialization failed: {type(e).__name__} - {str(e)}")
        logger.error(traceback.format_exc())
        raise e

async def close_postgres():
    global postgres_engine
    if postgres_engine:
        await postgres_engine.dispose()

async def init_mongo():
    global mongo_client
    mongo_client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGO_URI)
    # Ping to verify
    await mongo_client.admin.command('ping')

async def close_mongo():
    global mongo_client
    if mongo_client:
        mongo_client.close()

async def init_redis():
    global redis_client
    redis_client = aioredis.from_url(settings.REDIS_URI, decode_responses=True)
    # Ping to verify
    await redis_client.ping()

async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()

# FastAPI Dependencies
async def get_postgres_db() -> AsyncGenerator[Optional[AsyncSession], None]:
    if not postgres_session_factory:
        yield None
        return
    async with postgres_session_factory() as session:
        yield session

async def get_mongo_db():
    if not mongo_client:
        return None
    return mongo_client[settings.MONGO_DATABASE]

async def get_redis_client():
    if not redis_client:
        return None
    return redis_client
