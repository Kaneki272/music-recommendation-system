import uuid
from sqlalchemy import Column, String, Integer, DateTime, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.models.base import Base

class Song(Base):
    __tablename__ = "songs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    spotify_id = Column(String(100), unique=True, index=True)
    title = Column(String(255), nullable=False)
    album_id = Column(UUID(as_uuid=True), ForeignKey("albums.id"), nullable=False)
    artist_id = Column(UUID(as_uuid=True), ForeignKey("artists.id"), nullable=False)
    duration_ms = Column(Integer, nullable=False)
    isrc = Column(String(50))
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    album = relationship("Album", backref="songs")
    artist = relationship("Artist", backref="songs")
