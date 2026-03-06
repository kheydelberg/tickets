from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.sql import func
from app.database import Base

class ProcessedEvent(Base):
    """Для идемпотентной обработки Kafka событий"""
    __tablename__ = "processed_events"
    
    event_id = Column(String(100), primary_key=True)
    event_type = Column(String(50), nullable=False)
    processed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        Index('idx_processed_events_expires', 'expires_at'),
    )