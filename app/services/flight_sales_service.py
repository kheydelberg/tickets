from sqlalchemy.orm import Session
from app.models.flight_sales import FlightSales
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class FlightSalesService:
    """Управление продажами по рейсам"""
    
    @staticmethod
    def create_flight_sales(
        db: Session,
        flight_id: str,
        planned_capacity: int
    ) -> FlightSales:
        """
        F1: Инициализация продаж для нового рейса
        - создаём flight_sales с sales_open=true
        - overbook_limit = planned_capacity * overbook_factor
        """
        overbook_limit = int(planned_capacity * settings.overbook_factor)
        
        flight_sales = FlightSales(
            flight_id=flight_id,
            planned_capacity=planned_capacity,
            overbook_limit=overbook_limit,
            sold_total=0,
            active_total=0,
            sales_open=True
        )
        
        db.add(flight_sales)
        db.commit()
        db.refresh(flight_sales)
        
        logger.info(f"Created flight sales for {flight_id}: capacity={planned_capacity}, overbook={overbook_limit}")
        return flight_sales
    
    @staticmethod
    def close_sales(db: Session, flight_id: str) -> None:
        """
        F2: Закрытие продаж при старте регистрации
        - если newStatus == RegistrationOpen → sales_open=false
        - идемпотентно
        """
        flight_sales = db.query(FlightSales).filter(
            FlightSales.flight_id == flight_id
        ).first()
        
        if flight_sales and flight_sales.sales_open:
            flight_sales.sales_open = False
            db.commit()
            logger.info(f"Closed sales for flight {flight_id}")
        else:
            logger.info(f"Sales already closed for flight {flight_id}")