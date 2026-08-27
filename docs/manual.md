# MANUAL INTEGRATION GUIDE — Spotify API + Kafka Events + Real-Time Interaction Data

> **STATUS:** Reference Document — NONE of the steps below are currently automated.
> This guide documents what remains to be done manually to bring the system from
> its current offline-trained state to a live, real-time recommendation pipeline.

---

## Table of Contents

1. [What Exists Today (Scaffolding Inventory)](#1-what-exists-today)
2. [Spotify API Integration — Step by Step](#2-spotify-api-integration)
3. [Kafka Event Pipeline — Step by Step](#3-kafka-event-pipeline)
4. [Wiring Spotify Events into Kafka](#4-wiring-spotify-events-into-kafka)
5. [Alternatives for Real-Time User Interaction Data](#5-alternatives-for-real-time-interaction-data)
6. [Manual Checklist](#6-manual-checklist)

---

## 1. What Exists Today

Before starting manual work, understand what the codebase already provides:

| Component | File | Status |
| :--- | :--- | :--- |
| Spotify Client Interface | `ingestion/spotify_fetcher/client.py` | **INTERFACE ONLY** — `SpotifyClientInterface` with `fetch_artist()` and `fetch_album_tracks()`. No implementation. |
| Rate Limiter Interface | `ingestion/rate_limiter.py` | **INTERFACE ONLY** — `RateLimiterInterface`. No implementation. |
| Retry Decorator | `ingestion/retry_strategy.py` | **PLACEHOLDER** — `with_exponential_backoff` decorator exists but the retry loop is not implemented. |
| Kafka Event Schemas | `streaming/schemas/events.py` | **IMPLEMENTED** — Pydantic schemas for `SongPlayed`, `SongLiked`, `SongSkipped`, `PlaylistCreated`, `RecommendationServed`, `RecommendationClicked`, `RecommendationIgnored`. |
| Kafka Producers | `streaming/producers/` | **EMPTY** — `.gitkeep` only. |
| Kafka Consumers | `streaming/consumers/` | **EMPTY** — `.gitkeep` only. |
| Kafka Topics Config | `streaming/topics/` | **EMPTY** — `.gitkeep` only. |
| Docker Kafka | `docker-compose.yml` | **CONFIGURED** — Confluent Kafka 7.4.0 + Zookeeper ready to start. |
| Environment Variables | `.env.example` | **DEFINED** — `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `KAFKA_BROKERS` placeholders exist. |

**Bottom line:** The architecture is designed but the wiring is hollow. You must implement the concrete classes, the Kafka producer/consumer logic, and the Spotify OAuth flow.

---

## 2. Spotify API Integration — Step by Step

### Step 2.1 — Create a Spotify Developer Application

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. Log in with your Spotify account (or create one).
3. Click **"Create App"**.
4. Fill in:
   - **App Name:** `MusicRecSys`
   - **Description:** `Music Recommendation System — Research`
   - **Redirect URI:** `http://localhost:8888/callback` (required even for Client Credentials flow)
   - **APIs:** Select **Web API**
5. Click **"Save"**.
6. Copy the **Client ID** and **Client Secret** from the app settings page.

### Step 2.2 — Configure Environment

```bash
# In your project root, copy .env.example to .env
cp .env.example .env
```

Edit `.env`:
```env
SPOTIFY_CLIENT_ID=your_actual_client_id_here
SPOTIFY_CLIENT_SECRET=your_actual_client_secret_here
KAFKA_BROKERS=localhost:29092
```

> **IMPORTANT:** NEVER commit `.env` to Git. The `.gitignore` should already exclude it.

### Step 2.3 — Install `spotipy` (Spotify Python SDK)

```bash
pip install spotipy
```

Add to `requirements.txt`:
```
spotipy>=2.23.0
```

### Step 2.4 — Implement the Spotify Client

Create `ingestion/spotify_fetcher/spotify_client.py`:

```python
"""
Concrete Spotify API client implementing SpotifyClientInterface.
Uses Client Credentials flow (no user login needed for catalog data).
"""
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from typing import Dict, List, Optional
from ingestion.spotify_fetcher.client import SpotifyClientInterface


class SpotifyClient(SpotifyClientInterface):
    """
    Production Spotify client using spotipy.
    
    Authentication: Client Credentials Flow
    - Good for: fetching catalog metadata (tracks, artists, albums, audio features)
    - NOT good for: accessing user-specific data (playlists, listening history)
    
    For user-specific data, you need Authorization Code Flow (see Step 2.8).
    """

    def __init__(self):
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise ValueError(
                "SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in .env"
            )
        auth_manager = SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret,
        )
        self.sp = spotipy.Spotify(auth_manager=auth_manager)

    async def fetch_artist(self, spotify_id: str) -> dict:
        """Fetch artist metadata by Spotify artist ID."""
        return self.sp.artist(spotify_id)

    async def fetch_album_tracks(self, album_id: str) -> list[dict]:
        """Fetch all tracks from an album."""
        results = self.sp.album_tracks(album_id)
        tracks = results["items"]
        while results["next"]:
            results = self.sp.next(results)
            tracks.extend(results["items"])
        return tracks

    def fetch_track(self, track_id: str) -> dict:
        """Fetch a single track's metadata."""
        return self.sp.track(track_id)

    def fetch_audio_features(self, track_ids: List[str]) -> List[dict]:
        """
        Fetch Spotify's own audio features for up to 100 tracks at a time.
        NOTE: These are Spotify's features (danceability, energy, etc.),
        NOT our 215-D Librosa vectors. Do not confuse these.
        """
        results = []
        for i in range(0, len(track_ids), 100):
            batch = track_ids[i:i+100]
            results.extend(self.sp.audio_features(batch))
        return results

    def search_tracks(self, query: str, limit: int = 50) -> List[dict]:
        """Search Spotify catalog by query string."""
        results = self.sp.search(q=query, type="track", limit=min(limit, 50))
        return results["tracks"]["items"]
```

### Step 2.5 — Understand the Two Authentication Flows

| Flow | Use Case | User Login? | Scope |
| :--- | :--- | :--- | :--- |
| **Client Credentials** | Catalog metadata (tracks, artists, albums, audio features) | No | Public data only |
| **Authorization Code** | User listening history, playlists, currently playing | Yes | Requires user OAuth consent |

**For catalog ETL** (populating PostgreSQL with songs/artists/albums): Use **Client Credentials**.

**For real-time user activity** (what the user is currently listening to): Use **Authorization Code** (see Section 5 for alternatives).

### Step 2.6 — Authorization Code Flow (For User Data)

If you want to capture LIVE listening events from a Spotify user:

```python
"""
Authorization Code Flow — captures user-specific Spotify data.
Requires the user to log in via browser and grant permissions.
"""
import spotipy
from spotipy.oauth2 import SpotifyOAuth

scope = "user-read-recently-played user-read-currently-playing user-library-read"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    redirect_uri="http://localhost:8888/callback",
    scope=scope,
))

# Fetch the user's recently played tracks
recently_played = sp.current_user_recently_played(limit=50)
for item in recently_played["items"]:
    track = item["track"]
    played_at = item["played_at"]
    print(f"{played_at}: {track['name']} by {track['artists'][0]['name']}")
```

**Required Spotify Scopes:**
| Scope | What it provides |
| :--- | :--- |
| `user-read-recently-played` | Last 50 tracks played |
| `user-read-currently-playing` | What's playing RIGHT NOW |
| `user-library-read` | User's saved tracks/albums |
| `playlist-read-private` | User's private playlists |

### Step 2.7 — Map Spotify Data to Our Contracts

Spotify's API returns data in Spotify's format. You must map it to our existing `InteractionRecord` contract:

```python
from ml.contracts.interactions import InteractionRecord, InteractionType
from datetime import datetime

def spotify_play_to_interaction(spotify_item: dict, user_id: str) -> InteractionRecord:
    """Convert a Spotify 'recently played' item to our InteractionRecord."""
    track = spotify_item["track"]
    played_at = datetime.fromisoformat(spotify_item["played_at"].replace("Z", "+00:00"))
    
    return InteractionRecord(
        user_id=user_id,
        song_id=track["id"],  # Using Spotify track ID as song_id
        interaction_type=InteractionType.PLAY,
        timestamp=played_at,
        weight=1.0,  # Default PLAY weight from InteractionWeightConfig
        source="spotify",
        context_type="recently_played",
    )
```

> **WARNING:** Spotify track IDs are different from our Last.fm SHA-256 song_ids.
> You need an identity resolution layer to map Spotify IDs ↔ internal song_ids.
> This is a non-trivial problem (see Section 5.4).

---

## 3. Kafka Event Pipeline — Step by Step

### Step 3.1 — Start Kafka Infrastructure

```bash
# From project root
docker-compose up -d zookeeper kafka
```

Verify Kafka is running:
```bash
docker exec recsys-kafka kafka-topics --bootstrap-server localhost:9092 --list
```

### Step 3.2 — Create Kafka Topics

Create `streaming/topics/topic_config.py`:

```python
"""
Kafka topic definitions for the Music Recommendation System.
"""

TOPICS = {
    "user.interactions": {
        "partitions": 3,
        "replication_factor": 1,
        "description": "All user interaction events (play, like, skip, etc.)",
    },
    "recommendations.served": {
        "partitions": 2,
        "replication_factor": 1,
        "description": "Recommendation batches served to users",
    },
    "recommendations.feedback": {
        "partitions": 2,
        "replication_factor": 1,
        "description": "User clicks/ignores on served recommendations",
    },
    "catalog.updates": {
        "partitions": 1,
        "replication_factor": 1,
        "description": "New songs/artists added to catalog",
    },
}
```

Create topics manually via Docker:
```bash
docker exec recsys-kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --create --topic user.interactions \
  --partitions 3 --replication-factor 1

docker exec recsys-kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --create --topic recommendations.served \
  --partitions 2 --replication-factor 1

docker exec recsys-kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --create --topic recommendations.feedback \
  --partitions 2 --replication-factor 1
```

### Step 3.3 — Implement the Kafka Producer

Create `streaming/producers/interaction_producer.py`:

```python
"""
Kafka producer for user interaction events.
Serializes Pydantic event schemas to JSON and publishes to Kafka topics.
"""
import json
import os
from kafka import KafkaProducer
from streaming.schemas.events import BaseEvent


class InteractionProducer:
    """Publishes user interaction events to Kafka."""

    def __init__(self):
        brokers = os.getenv("KAFKA_BROKERS", "localhost:29092")
        self.producer = KafkaProducer(
            bootstrap_servers=brokers.split(","),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
            retries=3,
        )

    def publish_event(self, topic: str, event: BaseEvent) -> None:
        """
        Publish a single event to a Kafka topic.
        Uses user_id as the partition key for ordering guarantees.
        """
        self.producer.send(
            topic=topic,
            key=event.user_id,
            value=event.model_dump(mode="json"),
        )
        self.producer.flush()

    def close(self):
        self.producer.close()
```

### Step 3.4 — Implement the Kafka Consumer

Create `streaming/consumers/interaction_consumer.py`:

```python
"""
Kafka consumer for user interaction events.
Reads from Kafka, validates against Pydantic schemas, and persists to MongoDB.
"""
import json
import os
from kafka import KafkaConsumer
from streaming.schemas.events import SongPlayed, SongLiked, SongSkipped


EVENT_TYPE_MAP = {
    "SongPlayed": SongPlayed,
    "SongLiked": SongLiked,
    "SongSkipped": SongSkipped,
}


class InteractionConsumer:
    """Consumes interaction events and writes to MongoDB."""

    def __init__(self, group_id: str = "recsys-interaction-consumer"):
        brokers = os.getenv("KAFKA_BROKERS", "localhost:29092")
        self.consumer = KafkaConsumer(
            "user.interactions",
            bootstrap_servers=brokers.split(","),
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )

    def run(self):
        """
        Main consumer loop.
        
        For each message:
        1. Deserialize JSON
        2. Validate against Pydantic schema
        3. Convert to InteractionRecord
        4. Write to MongoDB
        5. Optionally update Redis feature cache
        """
        print("Consumer started. Waiting for messages...")
        for message in self.consumer:
            try:
                data = message.value
                event_type = data.get("event_type")
                
                # Validate against schema
                schema_class = EVENT_TYPE_MAP.get(event_type)
                if schema_class:
                    event = schema_class(**data)
                    self._process_event(event)
                else:
                    print(f"Unknown event type: {event_type}")
                    
            except Exception as e:
                print(f"Error processing message: {e}")
                # In production: send to dead-letter queue

    def _process_event(self, event):
        """
        Process a validated event.
        
        TODO: Implement these steps:
        1. Convert to InteractionRecord (ml/contracts/interactions.py)
        2. Insert into MongoDB interactions collection
        3. Update Redis user feature cache (for real-time recommendations)
        4. Optionally trigger feature store update
        """
        print(f"Processed: {type(event).__name__} for user {event.user_id}")
```

---

## 4. Wiring Spotify Events into Kafka

This is the critical integration point. Here's the complete data flow:

```
Spotify API → Poller/Webhook → Event Schema → Kafka Producer → Kafka Topic
                                                                    ↓
                                            Kafka Consumer → MongoDB + Redis
                                                                    ↓
                                                    Hybrid Engine (next request)
```

### Step 4.1 — Create the Spotify Poller

Since Spotify does not provide webhooks, you must poll their API periodically.

Create `streaming/workers/spotify_poller.py`:

```python
"""
Background worker that polls Spotify for recent user activity
and publishes events to Kafka.

Run as a standalone process:
    python -m streaming.workers.spotify_poller
"""
import asyncio
import os
import uuid
from datetime import datetime
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from streaming.schemas.events import SongPlayed
from streaming.producers.interaction_producer import InteractionProducer


POLL_INTERVAL_SECONDS = 30  # How often to check for new plays


class SpotifyPoller:
    """
    Polls Spotify's 'recently played' endpoint and emits SongPlayed events.
    
    Maintains a cursor (last_played_at) to avoid duplicating events.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.last_played_at = None
        self.producer = InteractionProducer()

        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
            redirect_uri="http://localhost:8888/callback",
            scope="user-read-recently-played",
        ))

    async def poll_once(self):
        """Fetch recent plays and publish new ones to Kafka."""
        kwargs = {"limit": 50}
        if self.last_played_at:
            # Spotify accepts 'after' as Unix timestamp in ms
            kwargs["after"] = int(self.last_played_at.timestamp() * 1000)

        results = self.sp.current_user_recently_played(**kwargs)

        new_events = 0
        for item in results.get("items", []):
            played_at = datetime.fromisoformat(
                item["played_at"].replace("Z", "+00:00")
            )

            # Skip if we've already seen this
            if self.last_played_at and played_at <= self.last_played_at:
                continue

            track = item["track"]
            event = SongPlayed(
                event_id=str(uuid.uuid4()),
                timestamp=played_at,
                user_id=self.user_id,
                song_id=track["id"],
                context_type=item.get("context", {}).get("type", "unknown"),
                context_id=item.get("context", {}).get("uri"),
                duration_played_ms=track["duration_ms"],
                completion_rate=1.0,  # recently_played = completed plays
            )

            self.producer.publish_event("user.interactions", event)
            new_events += 1

        # Update cursor
        if results.get("items"):
            latest = results["items"][0]
            self.last_played_at = datetime.fromisoformat(
                latest["played_at"].replace("Z", "+00:00")
            )

        return new_events

    async def run_forever(self):
        """Main polling loop."""
        print(f"Spotify poller started for user {self.user_id}")
        while True:
            try:
                count = await self.poll_once()
                if count > 0:
                    print(f"Published {count} new events")
            except Exception as e:
                print(f"Polling error: {e}")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    poller = SpotifyPoller(user_id="demo_user_001")
    asyncio.run(poller.run_forever())
```

### Step 4.2 — Summary of the Complete Wiring

```
┌─────────────────────────────────────────────────────────┐
│  MANUAL STEPS TO ACTIVATE REAL-TIME PIPELINE            │
│                                                         │
│  1. Create Spotify App → get Client ID + Secret         │
│  2. Set .env variables                                  │
│  3. docker-compose up -d zookeeper kafka                │
│  4. Create Kafka topics                                 │
│  5. Implement SpotifyClient (Step 2.4)                  │
│  6. Implement InteractionProducer (Step 3.3)            │
│  7. Implement InteractionConsumer (Step 3.4)            │
│  8. Implement SpotifyPoller (Step 4.1)                  │
│  9. Run poller: python -m streaming.workers.spotify_poller│
│ 10. Run consumer: python -m streaming.consumers.interaction_consumer│
│ 11. Verify events flow end-to-end                       │
└─────────────────────────────────────────────────────────┘
```

---

## 5. Alternatives for Real-Time User Interaction Data

Spotify's API has significant limitations for building a recommendation system:
- `recently_played` only returns the **last 50 tracks** (no full history).
- No webhook support — you must poll.
- Rate limits apply (undocumented but typically ~180 requests/minute).
- Authorization Code Flow requires each user to manually authenticate.

Here are practical alternatives:

### 5.1 — Self-Hosted Web Application (RECOMMENDED)

**Concept:** Build your own music player frontend. Every user action (play, pause, skip, like) fires an event directly to YOUR FastAPI backend, which publishes to Kafka.

**Advantages:**
- Full control over every interaction signal.
- No third-party API rate limits.
- You capture EXACTLY the events your models need (including skip timing, scroll behavior, dwell time).
- No identity resolution problem — your user_ids and song_ids are canonical from the start.

**Architecture:**
```
Browser/Mobile App
       ↓ (WebSocket or REST)
FastAPI Endpoint: POST /api/v1/events/interaction
       ↓
Validate against streaming/schemas/events.py
       ↓
Kafka Producer → "user.interactions" topic
       ↓
Kafka Consumer → MongoDB + Redis
```

**Implementation Sketch — FastAPI Event Endpoint:**
```python
from fastapi import APIRouter, Depends
from streaming.schemas.events import SongPlayed, SongLiked, SongSkipped
from streaming.producers.interaction_producer import InteractionProducer

router = APIRouter(prefix="/api/v1/events", tags=["events"])
producer = InteractionProducer()

@router.post("/play")
async def record_play(event: SongPlayed):
    producer.publish_event("user.interactions", event)
    return {"status": "accepted", "event_id": event.event_id}

@router.post("/like")
async def record_like(event: SongLiked):
    producer.publish_event("user.interactions", event)
    return {"status": "accepted", "event_id": event.event_id}

@router.post("/skip")
async def record_skip(event: SongSkipped):
    producer.publish_event("user.interactions", event)
    return {"status": "accepted", "event_id": event.event_id}
```

### 5.2 — Synthetic Event Simulator

**Concept:** Generate realistic fake user interactions programmatically to test the entire pipeline without needing real users.

**Advantages:**
- Zero external dependencies.
- Controllable volume (test with 10 events/sec or 10,000 events/sec).
- Reproducible with fixed random seeds.
- Perfect for load testing Kafka throughput.

**When to use:** During development and integration testing BEFORE you have real users.

**Implementation Sketch:**
```python
"""
Synthetic event generator for pipeline testing.
Produces realistic interaction events at configurable rates.
"""
import uuid
import random
import asyncio
from datetime import datetime
from streaming.schemas.events import SongPlayed, SongLiked, SongSkipped
from streaming.producers.interaction_producer import InteractionProducer


# Use real song_ids from your catalog
SAMPLE_SONGS = ["song_001", "song_002", "song_003", ...]
SAMPLE_USERS = ["user_001", "user_002", "user_003", ...]


async def generate_events(events_per_second: float = 1.0):
    producer = InteractionProducer()
    
    while True:
        user_id = random.choice(SAMPLE_USERS)
        song_id = random.choice(SAMPLE_SONGS)
        
        # 70% plays, 15% likes, 15% skips
        roll = random.random()
        if roll < 0.70:
            event = SongPlayed(
                event_id=str(uuid.uuid4()),
                user_id=user_id,
                song_id=song_id,
                context_type="radio",
                duration_played_ms=random.randint(30000, 240000),
                completion_rate=random.uniform(0.3, 1.0),
            )
        elif roll < 0.85:
            event = SongLiked(
                event_id=str(uuid.uuid4()),
                user_id=user_id,
                song_id=song_id,
            )
        else:
            event = SongSkipped(
                event_id=str(uuid.uuid4()),
                user_id=user_id,
                song_id=song_id,
                duration_played_ms=random.randint(3000, 30000),
                skip_timestamp_ms=random.randint(3000, 30000),
            )
        
        producer.publish_event("user.interactions", event)
        await asyncio.sleep(1.0 / events_per_second)
```

### 5.3 — Last.fm Scrobble API (Real Historical Data)

**Concept:** Use the Last.fm API to fetch real listening history from Last.fm users (with their permission).

**Advantages:**
- REAL interaction data from real music listeners.
- Much richer history than Spotify's 50-track limit.
- Free API with reasonable rate limits.
- Already partially compatible with our Last.fm 1K dataset.

**API Endpoint:**
```
GET https://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks
    &user=USERNAME
    &api_key=YOUR_API_KEY
    &format=json
    &limit=200
    &page=1
```

**Steps:**
1. Get a Last.fm API key at [last.fm/api/account/create](https://www.last.fm/api/account/create).
2. Add `LASTFM_API_KEY` to `.env`.
3. Fetch recent tracks and convert to `InteractionRecord` format.
4. Publish to Kafka or write directly to MongoDB.

### 5.4 — Browser Extension Scrobbler

**Concept:** Build a lightweight browser extension that captures what the user listens to on YouTube Music, SoundCloud, Bandcamp, or any web-based player.

**Advantages:**
- Works across multiple music platforms simultaneously.
- Captures interactions that no single API can provide.
- User installs once, data flows continuously.

**Disadvantages:**
- Requires building and maintaining a browser extension.
- Privacy implications must be clearly communicated.
- Song identification requires matching page metadata to your catalog.

### 5.5 — Comparison Table

| Method | Real Data? | Setup Effort | Rate Limits | Full History? | Identity Resolution? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Self-Hosted App** | Yes | High | None | Yes | Not needed |
| **Synthetic Simulator** | No | Low | None | Configurable | Not needed |
| **Spotify API** | Yes | Medium | Yes (strict) | No (50 tracks) | Spotify ID → internal |
| **Last.fm API** | Yes | Low | Yes (lenient) | Yes (paginated) | MusicBrainz ID available |
| **Browser Extension** | Yes | Very High | None | Yes | Complex metadata matching |

---

## 6. Manual Checklist

Use this checklist to track your progress through the manual integration:

### Prerequisites
- [ ] Spotify Developer Account created
- [ ] Spotify App registered (Client ID + Secret obtained)
- [ ] `.env` file created from `.env.example` with real credentials
- [ ] Docker Desktop installed and running
- [ ] `spotipy` installed (`pip install spotipy`)

### Kafka Infrastructure
- [ ] `docker-compose up -d zookeeper kafka` successful
- [ ] Kafka topics created (`user.interactions`, `recommendations.served`, `recommendations.feedback`)
- [ ] Kafka topic list verified via `docker exec`

### Spotify Client
- [ ] `ingestion/spotify_fetcher/spotify_client.py` implemented
- [ ] Client Credentials flow tested (fetch a known track)
- [ ] Authorization Code flow tested (fetch recently played)

### Kafka Producer
- [ ] `streaming/producers/interaction_producer.py` implemented
- [ ] Unit test: publish a test event, verify it appears in topic

### Kafka Consumer
- [ ] `streaming/consumers/interaction_consumer.py` implemented
- [ ] Consumer correctly deserializes events
- [ ] Consumer writes to MongoDB
- [ ] Consumer updates Redis feature cache

### Integration Test
- [ ] Spotify Poller → Kafka → Consumer → MongoDB end-to-end verified
- [ ] Event counts match: produced == consumed
- [ ] No data loss or duplication

### Alternative Data Source (if not using Spotify)
- [ ] Chosen alternative: ________________________________
- [ ] Data mapping to `InteractionRecord` contract verified
- [ ] End-to-end pipeline tested

---

> **NOTE:** This document describes what must be done MANUALLY.
> None of these steps have been automated or executed.
> The code snippets above are reference implementations — they must be
> reviewed, tested, and adapted before production use.
