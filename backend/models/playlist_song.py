import uuid
from sqlalchemy import Column, Integer, DateTime, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from backend.models.base import Base

class PlaylistSong(Base):
    __tablename__ = "playlist_songs"

    playlist_id = Column(UUID(as_uuid=True), ForeignKey("playlists.id"), primary_key=True)
    song_id = Column(UUID(as_uuid=True), ForeignKey("songs.id"), primary_key=True)
    position = Column(Integer, nullable=False)
    added_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    added_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
