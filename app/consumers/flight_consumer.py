from app.consumers.base import BaseConsumer
from app.services.flight_sales_service import FlightSalesService
from app.database import SessionLocal
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class FlightConsumer(BaseConsumer):
    """
    Слушает flights.events
    Обрабатывает:
    - flight.created → создание flight_sales
    - flight.status.changed → закрытие продаж при RegistrationOpen
    """
    
    def __init__(self):
        super().__init__(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            topic=settings.kafka_topic_flights_events,
            group_id="ticket-sales-flight-consumer"
        )
        self.register_handler('flight.created', self.handle_flight_created)
        self.register_handler('flight.status.changed', self.handle_flight_status_changed)
    
    async def handle_flight_created(self, message):
        """F1: Инициализация продаж для нового рейса"""
        payload = message.get('payload', {})
        flight_id = payload.get('flightId')
        planned_capacity = payload.get('plannedCapacity')
        
        if not flight_id or not planned_capacity:
            logger.error(f"Invalid flight.created message: {message}")
            return
        
        db = SessionLocal()
        try:
            FlightSalesService.create_flight_sales(db, flight_id, planned_capacity)
            logger.info(f"Initialized sales for flight {flight_id}")
        finally:
            db.close()
    
    async def handle_flight_status_changed(self, message):
        """F2: Закрытие продаж при старте регистрации"""
        payload = message.get('payload', {})
        flight_id = payload.get('flightId')
        new_status = payload.get('newStatus')
        
        if not flight_id or not new_status:
            logger.error(f"Invalid flight.status.changed message: {message}")
            return
        
        if new_status == 'RegistrationOpen':
            db = SessionLocal()
            try:
                FlightSalesService.close_sales(db, flight_id)
                logger.info(f"Closed sales for flight {flight_id}")
            finally:
                db.close()