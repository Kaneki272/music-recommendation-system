# Real Local Infrastructure

The Music Recommendation System local development environment is powered by a multi-container Docker Compose setup. This document outlines the services, their responsibilities, and how to operate the environment.

## Architecture

* **PostgreSQL (Port 5432)**: Stores structured/relational entity data (users, songs, albums, artists).
* **MongoDB (Port 27017)**: Stores high-volume interaction and event history (e.g., `music_interactions` collection).
* **Redis (Port 6379)**: Maintains low-latency user state and recent track history for the hybrid recommender.
* **Kafka (Port 9092)** & **Zookeeper (Port 2181)**: The asynchronous event backbone processing `MusicEvent` streams.
* **Qdrant (Port 6333)**: Vector database for content-based similarity.

## Configuration (Environment Variables)

Configuration is managed securely via `backend/config/settings.py` mapping to `.env`.

Required variables:
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `MONGO_URI`, `MONGO_DATABASE`
- `REDIS_HOST`, `REDIS_PORT`
- `KAFKA_BOOTSTRAP_SERVERS`

*(See `.env.example` for all required variables).*

## Startup Commands

Start the full stack:
```bash
docker compose up -d
```

Initialize the Kafka topics (must be run once before producers/consumers start):
```bash
python scripts/create_kafka_topics.py
```

Start the Kafka consumer (runs independently of FastAPI):
```bash
python -m streaming.consumers.interaction_consumer
```

Start the FastAPI application (e.g., using `uvicorn`):
```bash
cd backend && uvicorn main:app --reload
```

## Shutdown & Reset

To cleanly shut down the infrastructure:
```bash
docker compose down
```

### **Resetting Database State**
Because persistent Docker volumes are used (`postgres_data`, `mongo_data`, `redis_data`), your data survives restarts. If you need to **completely wipe** all data and start fresh, run:
```bash
docker compose down -v
```
**Warning**: This destroys all local database records!

## Health Checks

Once the FastAPI application is running (e.g. at `http://localhost:8000`), you can verify infrastructure health via:
* `GET /health` : App status
* `GET /health/db` : PostgreSQL and MongoDB physical connectivity
* `GET /health/streaming` : Redis and Kafka cluster connectivity
