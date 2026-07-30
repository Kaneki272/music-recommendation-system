import uuid
from sqlalchemy import Column, String, DateTime, text, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.models.base import Base

class Album(Base):
    __tablename__ = "albums"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    spotify_id = Column(String(100), unique=True, index=True)
    title = Column(String(255), nullable=False)
    artist_id = Column(UUID(as_uuid=True), ForeignKey("artists.id"), nullable=False)
    release_date = Column(Date)
    cover_image_url = Column(String)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    artist = relationship("Artist", backref="albums")
