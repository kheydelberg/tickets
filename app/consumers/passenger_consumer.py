from app.consumers.base import BaseConsumer
from app.services.ticket_service import TicketService
from app.database import SessionLocal
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class PassengerConsumer(BaseConsumer):
    """
    Слушает passengers.events
    Обрабатывает:
    - passenger.created → авто-покупка билета
    """
    
    def __init__(self):
        super().__init__(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            topic=settings.kafka_topic_passengers_events,
            group_id="ticket-sales-passenger-consumer"
        )
        self.register_handler('passenger.created', self.handle_passenger_created)
    
    async def handle_passenger_created(self, message):
        """F3: Авто-покупка билета для нового пассажира"""
        payload = message.get('payload', {})
        
        required_fields = ['passengerId', 'passengerName', 'flightId']
        if not all(field in payload for field in required_fields):
            logger.error(f"Invalid passenger.created message: {message}")
            return
        
        db = SessionLocal()
        try:
            # Пробуем купить билет
            ticket = TicketService.buy_ticket(
                db=db,
                passenger_id=payload['passengerId'],
                passenger_name=payload['passengerName'],
                flight_id=payload['flightId'],
                is_vip=payload.get('isVIP', False),
                menu_type=payload.get('menuType'),
                baggage_weight=payload.get('baggageWeight', 0)
            )
            
            if ticket:
                logger.info(f"Auto-bought ticket for passenger {payload['passengerId']}")
            else:
                # По документации: если не получилось, пассажир остается без билета
                logger.info(f"Could not auto-buy ticket for passenger {payload['passengerId']}")
                
        except Exception as e:
            logger.error(f"Error auto-buying ticket: {e}")
        finally:
            db.close()