from app.consumers.base import BaseConsumer
from app.services.ticket_service import TicketService
from app.database import SessionLocal
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class BoardingConsumer(BaseConsumer):
    """
    Слушает board.events
    Обрабатывает:
    - board.boarding.result → обработка овербукинга
    """
    
    def __init__(self):
        super().__init__(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            topic=settings.kafka_topic_board_events,
            group_id="ticket-sales-boarding-consumer"
        )
        self.register_handler('board.boarding.result', self.handle_boarding_result)
    
    async def handle_boarding_result(self, message):
        """F6: Обработка результатов посадки (overbooking)"""
        payload = message.get('payload', {})
        
        flight_id = payload.get('flightId')
        bumped_passenger_ids = payload.get('bumpedPassengerIds', [])
        
        if not flight_id:
            logger.error(f"Invalid board.boarding.result message: {message}")
            return
        
        if bumped_passenger_ids:
            db = SessionLocal()
            try:
                TicketService.process_boarding_result(
                    db=db,
                    flight_id=flight_id,
                    bumped_passenger_ids=bumped_passenger_ids
                )
                logger.info(f"Processed boarding result for flight {flight_id}, bumped: {len(bumped_passenger_ids)}")
            finally:
                db.close()