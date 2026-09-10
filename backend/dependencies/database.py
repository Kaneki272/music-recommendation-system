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
