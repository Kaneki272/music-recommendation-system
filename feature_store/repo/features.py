"""
Feast Feature Views
===================
Defines structured ML features for online and offline retrieval.
Offline features are backed by FileSource (parquet) for simple local development.
"""
from datetime import timedelta
from feast import FeatureView, Field
from feast.types import Int64, Float32, String, Bool
from feast.infra.offline_stores.file_source import FileSource

from entities import song, user


# --- Data Sources ---
# In a local setup, we simulate the offline store with Parquet files.
# The sync pipeline will generate these from PostgreSQL/MongoDB.
song_metadata_source = FileSource(
    path="data/song_metadata.parquet",
    timestamp_field="event_timestamp",
)

user_behavior_source = FileSource(
    path="data/user_behavior.parquet",
    timestamp_field="event_timestamp",
)


# --- Feature Views ---

song_metadata_fv = FeatureView(
    name="song_metadata",
    entities=[song],
    ttl=timedelta(days=3650), # Metadata rarely expires
    schema=[
        Field(name="duration_ms", dtype=Int64),
        Field(name="explicit", dtype=Bool),
        Field(name="release_year", dtype=Int64),
        Field(name="genres", dtype=String), # Stored as JSON string or comma-separated
        Field(name="artist_popularity", dtype=Float32),
    ],
    online=True,
    source=song_metadata_source,
    tags={"team": "discovery"},
)


user_behavior_fv = FeatureView(
    name="user_behavior",
    entities=[user],
    ttl=timedelta(days=30), # Recompute behavioral features every 30 days
    schema=[
        Field(name="listening_history_count", dtype=Int64),
        Field(name="recently_played_ids", dtype=String), # JSON string
        Field(name="favorite_genres", dtype=String), # JSON string
        Field(name="acoustic_preferences", dtype=String), # JSON string
    ],
    online=True,
    source=user_behavior_source,
    tags={"team": "personalization"},
)
