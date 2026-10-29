import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class BotEnvVar(Base):
    __tablename__ = "bot_env_vars"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    bot_id = Column(String(36), ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True)
    key = Column(String(100), nullable=False)
    encrypted_value = Column(String(1000), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    bot = relationship("Bot", back_populates="env_vars")

    __table_args__ = (
        UniqueConstraint("bot_id", "key", name="uq_bot_env_key"),
    )
