# Infrastructure Audit

**Date:** 2026-09-03
**Status:** Pre-Implementation

## 1. Which database components already work?
- **Qdrant**: The asynchronous Qdrant client (`backend/database/qdrant/client.py`) works and is verified.
- **FastAPI**: The backend entry point (`backend/main.py`) exists but lacks real routes/database integrations.

## 2. Which components are placeholders?
- **Database Dependencies**: `backend/dependencies/database.py` contains empty async generators (`get_postgres_db`, `get_mongo_db`, `get_redis_client`).
- **Kafka Producer/Consumer**: Previously implemented with a simulated MongoDB insert (mocked persistence). They do not connect to real Redis or Mongo.
- **Redis Integration**: Non-existent (only a `.gitkeep` and `docker-compose` service).
- **Configuration**: No centralized `settings.py` or configuration loader. `.env.example` exists with placeholders.

## 3. Which MongoDB models already exist?
- `backend/models/mongo/tracking.py` defines Pydantic schemas: `ListeningHistory`, `UserInteraction`, `RecommendationHistory`, `UserPreference`.

## 4. Which PostgreSQL models already exist?
- `backend/models/base.py` defines the SQLAlchemy Base.
- Models: `song.py`, `album.py`, `artist.py`, `user.py`, `playlist.py`, `playlist_song.py`, `rbac.py`, `refresh_token.py`, `etl_tracking.py`.
- *Missing:* No SQLAlchemy Engine or SessionMaker is initialized.

## 5. Which Kafka components already exist?
- `streaming/schemas/events.py`: Contains `BaseEvent`, `SongPlayed`, `SongLiked`, etc. (Needs improvement to a canonical `MusicEvent` as requested).
- `streaming/topics/topic_config.py` & `scripts/create_kafka_topics.py`: Exists.
- `streaming/producers/interaction_producer.py`: Serializes and publishes events to `user.interactions`.
- `streaming/consumers/interaction_consumer.py`: Consumes events but simulates MongoDB writes.

## 6. Which Redis components already exist?
- Only a service entry in `docker-compose.yml`. No python client or consumer logic.

## 7. Which environment variables are already defined?
- In `.env.example`: `POSTGRES_URI`, `MONGO_URI`, `REDIS_URI`, `QDRANT_URI`, `KAFKA_BROKERS`, `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `JWT_SECRET_KEY`, `MODEL_CHECKPOINT_DIR`.

## 8. Which Docker services already exist?
- `docker-compose.yml` defines: `api`, `frontend`, `postgres`, `mongo`, `redis`, `qdrant`, `zookeeper`, `kafka`. All have appropriate images, environment variables, ports, and named volumes.

## 9. Which code should be preserved?
- Existing SQLAlchemy models in `backend/models/`.
- Existing `docker-compose.yml` (architecture is sound, just needs verifying KRaft vs Zookeeper; currently uses Zookeeper which is fine to preserve).
- Existing `streaming/schemas/events.py` (can be enhanced rather than overwritten).
- `backend/models/mongo/tracking.py` (can be adapted).

## 10. Which code must be modified / Required changes?
| Component | Current State | Problem | Required Change | Files Affected |
| :--- | :--- | :--- | :--- | :--- |
| **PostgreSQL setup** | Placeholder | SQLAlchemy models exist but cannot be queried. | Add engine, session maker, and healthcheck. Add asyncpg or psycopg2 to requirements. | `backend/dependencies/database.py`, `backend/main.py`, `requirements.txt` |
| **MongoDB setup** | Placeholder | Consumer mocks DB insert. | Initialize Motor client, create unique indexes on `event_id`. | `backend/dependencies/database.py`, `streaming/consumers/interaction_consumer.py` |
| **Redis setup** | Missing | No low-latency state tracking. | Initialize Redis client, add Redis consumer logic for `user.interactions`. | `backend/dependencies/database.py`, `streaming/consumers/interaction_consumer.py` (or new redis consumer) |
| **Configuration** | Missing | Hardcoded env reads in some places. | Add `backend/config/settings.py` for pydantic BaseSettings. | `backend/config/settings.py`, `.env.example` |
| **MusicEvent** | Fragmented | Multiple specific schemas (SongPlayed). | Unify into canonical source-independent `MusicEvent`. | `streaming/schemas/events.py`, `streaming/producers/interaction_producer.py` |
| **Health Checks** | Missing | App has no endpoints. | Add `/health`, `/health/db`, `/health/streaming`. | `backend/main.py` |
