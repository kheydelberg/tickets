from aiokafka import AIOKafkaConsumer
import asyncio
import json
import logging
from typing import Callable, Dict, Any
from app.database import SessionLocal
from app.utils.idempotency import IdempotencyUtils

logger = logging.getLogger(__name__)

class BaseConsumer:
    """Базовый класс для всех Kafka consumers"""
    
    def __init__(self, bootstrap_servers: str, topic: str, group_id: str):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.consumer = None
        self.handlers: Dict[str, Callable] = {}
    
    async def start(self):
        """Запуск consumer"""
        self.consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=False  # Ручной commit для идемпотентности
        )
        
        await self.consumer.start()
        logger.info(f"Started consumer for topic {self.topic}")
        
        try:
            async for msg in self.consumer:
                await self.process_message(msg.value)
                await self.consumer.commit()  # Коммитим после успешной обработки
        finally:
            await self.consumer.stop()
    
    async def process_message(self, message: Dict[str, Any]):
        """Обработка сообщения с идемпотентностью"""
        event_id = message.get('eventId')
        event_type = message.get('type')
        
        if not event_id or not event_type:
            logger.error(f"Invalid message format: {message}")
            return
        
        db = SessionLocal()
        try:
            # Проверяем дубликаты (inbox pattern из документации)
            if IdempotencyUtils.is_event_processed(db, event_id):
                logger.info(f"Event {event_id} already processed, skipping")
                return
            
            # Вызываем соответствующий обработчик
            handler = self.handlers.get(event_type)
            if handler:
                await handler(message)
            else:
                logger.warning(f"No handler for event type {event_type}")
            
            # Помечаем как обработанное
            IdempotencyUtils.mark_event_processed(db, event_id, event_type)
            db.commit()
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error processing message {event_id}: {e}")
            raise  # Пробрасываем, чтобы не коммитить offset
        finally:
            db.close()
    
    def register_handler(self, event_type: str, handler: Callable):
        """Регистрация обработчика для типа события"""
        self.handlers[event_type] = handler