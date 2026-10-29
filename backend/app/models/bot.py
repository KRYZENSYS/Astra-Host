import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


class Bot(Base):
    __tablename__ = "bots"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    entrypoint = Column(String(255), default="main.py", nullable=False)
    has_requirements = Column(Boolean, default=False, nullable=False)
    container_id = Column(String(100), nullable=True)
    status = Column(String(30), default="created", nullable=False, index=True)
    # Status lifecycle: created -> building -> build_failed | stopped -> starting -> running -> crashed | stopped
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    owner = relationship("User", back_populates="bots")
    env_vars = relationship("BotEnvVar", back_populates="bot", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_bots_user_status", "user_id", "status"),
    )
