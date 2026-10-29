import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Float, Index
from app.database import Base


class Node(Base):
    """
    Represents an infrastructure worker host in a multi-node BotHost cluster.
    Enables node-aware scheduling and capacity reservations.
    """
    __tablename__ = "nodes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False)
    ip_address = Column(String(45), nullable=False)
    status = Column(String(20), default="healthy", nullable=False)  # healthy, draining, offline
    total_ram_mb = Column(Integer, default=16384, nullable=False)   # 16 GB default
    used_ram_mb = Column(Integer, default=0, nullable=False)
    total_cpu_cores = Column(Float, default=8.0, nullable=False)
    used_cpu_cores = Column(Float, default=0.0, nullable=False)
    max_bots = Column(Integer, default=100, nullable=False)
    current_bots_count = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_heartbeat = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_nodes_status_active", "status", "is_active"),
    )
