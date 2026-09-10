import re
import urllib.parse
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import Optional

class Settings(BaseSettings):
    # Database Configurations
    POSTGRES_URI: Optional[str] = None
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "recsys"
    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "password"

    MONGO_URI: str = "mongodb://user:password@localhost:27017/"
    MONGO_DATABASE: str = "recsys"

    REDIS_URI: Optional[str] = None
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    QDRANT_URI: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None

    @model_validator(mode="after")
    def assemble_database_uris(self) -> "Settings":
        # 1. POSTGRES
        raw_pg = self.POSTGRES_URI
        if not raw_pg:
            clean_host = self.POSTGRES_HOST.strip().replace("https://", "").replace("http://", "").rstrip("/")
            if "/rest/v1" in clean_host:
                clean_host = clean_host.replace("/rest/v1", "")
            m = re.search(r"([a-z0-9]+)\.supabase\.co", clean_host)
            if m and not clean_host.startswith("db.") and "pooler" not in clean_host:
                clean_host = f"db.{m.group(1)}.supabase.co"
            quoted_pw = urllib.parse.quote_plus(self.POSTGRES_PASSWORD)
            self.POSTGRES_URI = f"postgresql+asyncpg://{self.POSTGRES_USER}:{quoted_pw}@{clean_host}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        else:
            uri = raw_pg.strip().strip('"').strip("'")
            if "@" not in uri:
                m = re.search(r"([a-z0-9]+)\.supabase\.co", uri)
                if m:
                    ref = m.group(1)
                    quoted_pw = urllib.parse.quote_plus(self.POSTGRES_PASSWORD)
                    uri = f"postgresql+asyncpg://postgres:{quoted_pw}@db.{ref}.supabase.co:5432/{self.POSTGRES_DB}"
            else:
                if uri.startswith("postgres://"):
                    uri = "postgresql+asyncpg://" + uri[11:]
                elif uri.startswith("postgresql://"):
                    uri = "postgresql+asyncpg://" + uri[13:]
                prefix, at, rest = uri.partition("@")
                scheme_user, colon, pw = prefix.rpartition(":")
                if colon and pw:
                    quoted_pw = urllib.parse.quote(urllib.parse.unquote_plus(pw), safe="")
                    uri = f"{scheme_user}:{quoted_pw}@{rest}"
            self.POSTGRES_URI = uri

        # 2. REDIS
        raw_redis = self.REDIS_URI
        if raw_redis:
            uri = raw_redis.strip().strip('"').strip("'")
            if " -u " in uri:
                uri = uri.split(" -u ")[-1].strip()
            if "redis://" in uri and "upstash.io" in uri:
                uri = uri.replace("redis://", "rediss://", 1)
            self.REDIS_URI = uri
        else:
            if self.REDIS_HOST.startswith("redis://") or self.REDIS_HOST.startswith("rediss://"):
                self.REDIS_URI = self.REDIS_HOST
            else:
                self.REDIS_URI = f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

        return self

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_INTERACTION_TOPIC: str = "user.interactions"
    KAFKA_RECOMMENDATION_TOPIC: str = "recommendations.served"
    KAFKA_FEEDBACK_TOPIC: str = "recommendations.feedback"

    # APIs
    SPOTIFY_CLIENT_ID: Optional[str] = None
    SPOTIFY_CLIENT_SECRET: Optional[str] = None

    # Security
    JWT_SECRET_KEY: str = "secret"

    # ML
    MODEL_CHECKPOINT_DIR: str = "/models/checkpoints"
    MAX_AUDIO_UPLOAD_SIZE_MB: int = 20


    # CORS
    FRONTEND_CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()
