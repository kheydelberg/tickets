from sqlalchemy.orm import Session
from app.models.processed_events import ProcessedEvent
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class IdempotencyUtils:
    """Утилиты для идемпотентной обработки событий"""
    
    @staticmethod
    def is_event_processed(db: Session, event_id: str) -> bool:
        """Проверка, обработано ли событие (inbox pattern)"""
        return db.query(ProcessedEvent).filter(
            ProcessedEvent.event_id == event_id
        ).first() is not None
    
    @staticmethod
    def mark_event_processed(
        db: Session,
        event_id: str,
        event_type: str,
        ttl_days: int = 7
    ) -> None:
        """Пометить событие как обработанное"""
        # Очищаем старые записи
        cutoff = datetime.utcnow() - timedelta(days=ttl_days)
        db.query(ProcessedEvent).filter(
            ProcessedEvent.processed_at < cutoff
        ).delete()
        
        # Добавляем новое событие
        event = ProcessedEvent(
            event_id=event_id,
            event_type=event_type,
            expires_at=datetime.utcnow() + timedelta(days=ttl_days)
        )
        db.add(event)
        logger.debug(f"Marked event {event_id} as processed")
    
    @staticmethod
    def get_idempotency_key_from_headers(headers: dict) -> str:
        """Получение idempotency-key из заголовков"""
        return headers.get('idempotency-key') or headers.get('Idempotency-Key')