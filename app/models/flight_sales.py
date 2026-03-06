from sqlalchemy import Column, String, Integer, Boolean, DateTime, Index, CheckConstraint
from sqlalchemy.sql import func
from app.database import Base

class FlightSales(Base):
    __tablename__ = "flight_sales"
    
    flight_id = Column(String(50), primary_key=True)
    planned_capacity = Column(Integer, nullable=False)
    overbook_limit = Column(Integer, nullable=False)  # planned_capacity * overbook_factor
    sold_total = Column(Integer, default=0, nullable=False)
    active_total = Column(Integer, default=0, nullable=False)
    sales_open = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        CheckConstraint('planned_capacity > 0', name='check_planned_capacity_positive'),
        CheckConstraint('overbook_limit >= 0', name='check_overbook_limit_non_negative'),
        CheckConstraint('sold_total >= 0', name='check_sold_total_non_negative'),
        CheckConstraint('active_total >= 0', name='check_active_total_non_negative'),
        CheckConstraint('active_total <= sold_total', name='check_active_not_exceed_sold'),
    )
    
    @property
    def total_limit(self) -> int:
        """Максимальное количество билетов с учетом овербукинга"""
        return self.planned_capacity + self.overbook_limit
    
    def to_dict(self):
        return {
            'flightId': self.flight_id,
            'plannedCapacity': self.planned_capacity,
            'overbookLimit': self.overbook_limit,
            'soldTotal': self.sold_total,
            'activeTotal': self.active_total,
            'salesOpen': self.sales_open,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }