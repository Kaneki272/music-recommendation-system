import uuid
from sqlalchemy import Column, String, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from backend.models.base import Base

class Artist(Base):
    __tablename__ = "artists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    spotify_id = Column(String(100), unique=True, index=True)
    name = Column(String(255), nullable=False)
    bio = Column(String)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
