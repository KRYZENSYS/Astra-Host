import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Index, ForeignKey
from app.database import Base


class Job(Base):
    """
    Tracks asynchronous background execution tasks (builds, zip extraction, backups, container start/stop).
    Enables stateless request-response cycles and progress polling.
    """
    __tablename__ = "background_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    bot_id = Column(String(36), nullable=True, index=True)
    job_type = Column(String(50), nullable=False)  # build_and_deploy, start_container, stop_container, create_backup, update_code
    status = Column(String(30), default="queued", nullable=False)  # queued, processing, completed, failed
    progress_percent = Column(Integer, default=0, nullable=False)
    stage_message = Column(String(255), default="Vazifa navbatga qo'yildi", nullable=False)
    result_data = Column(Text, nullable=True)  # JSON-encoded result if any
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_jobs_user_status", "user_id", "status"),
        Index("idx_jobs_created", "created_at"),
    )
