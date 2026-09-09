from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Database Configurations
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "recsys"
    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "password"
    
    @property
    def POSTGRES_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    MONGO_URI: str = "mongodb://user:password@localhost:27017/"
    MONGO_DATABASE: str = "recsys"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    
    @property
    def REDIS_URI(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    QDRANT_URI: str = "http://localhost:6333"

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
