from sqlalchemy import Column, String, JSON, DateTime, Integer, Index
from sqlalchemy.sql import func
from app.database import Base
import uuid

class OutboxMessage(Base):
    """Transactional Outbox pattern для надежной отправки в Kafka"""
    __tablename__ = "outbox_messages"
    
    id = Column(String(100), primary_key=True, default=lambda: str(uuid.uuid4()))
    topic = Column(String(100), nullable=False)
    key = Column(String(255), nullable=True)
    value = Column(JSON, nullable=False)
    status = Column(String(20), default="pending", nullable=False)  # pending, sent, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    
    __table_args__ = (
        Index('idx_outbox_status_created', 'status', 'created_at'),
    )