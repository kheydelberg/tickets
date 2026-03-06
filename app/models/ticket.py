from sqlalchemy import Column, String, Integer, Boolean, DateTime, Enum, Index, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import enum
import uuid

class TicketStatusEnum(enum.Enum):
    """Статусы билетов из документации: active/returned/bumped/fake"""
    ACTIVE = "active"
    RETURNED = "returned"
    BUMPED = "bumped"
    FAKE = "fake"

class Ticket(Base):
    __tablename__ = "tickets"
    
    ticket_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    passenger_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    passenger_name = Column(String(255), nullable=False)
    flight_id = Column(String(50), nullable=False, index=True)
    status = Column(Enum(TicketStatusEnum), default=TicketStatusEnum.ACTIVE, nullable=False)
    is_vip = Column(Boolean, default=False, nullable=False)
    menu_type = Column(String(20), nullable=True)
    baggage_weight = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Индексы для быстрых запросов
    __table_args__ = (
        Index('idx_tickets_flight_status', 'flight_id', 'status'),
        Index('idx_tickets_passenger_flight', 'passenger_id', 'flight_id'),
        CheckConstraint('baggage_weight >= 0', name='check_baggage_weight_non_negative'),
    )
    
    def to_dict(self):
        return {
            'ticketId': str(self.ticket_id),
            'passengerId': str(self.passenger_id),
            'passengerName': self.passenger_name,
            'flightId': self.flight_id,
            'status': self.status.value,
            'isVIP': self.is_vip,
            'menuType': self.menu_type,
            'baggageWeight': self.baggage_weight,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }