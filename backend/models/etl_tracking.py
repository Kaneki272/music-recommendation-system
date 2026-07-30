import uuid
from sqlalchemy import Column, String, Integer, DateTime, text, JSON
from sqlalchemy.dialects.postgresql import UUID
from backend.models.base import Base

class ImportJob(Base):
    __tablename__ = "etl_import_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_name = Column(String(100), nullable=False, index=True)
    status = Column(String(50), nullable=False) # e.g., RUNNING, COMPLETED, FAILED
    records_processed = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    started_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    finished_at = Column(DateTime)

class SyncState(Base):
    __tablename__ = "etl_sync_states"

    provider = Column(String(50), primary_key=True) # e.g., spotify
    entity_type = Column(String(50), primary_key=True) # e.g., albums
    last_cursor = Column(String(255), nullable=False)
    updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

class FailedRecord(Base):
    __tablename__ = "etl_failed_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), nullable=False)
    raw_data = Column(JSON, nullable=False)
    error_reason = Column(String, nullable=False)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
