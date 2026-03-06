# app/consumers/base.py
from aiokafka import AIOKafkaConsumer
import asyncio
import json
import logging
from typing import Callable, Dict, Any, Optional
from app.database import SessionLocal
from app.utils.idempotency import IdempotencyUtils
from app.config import settings

logger = logging.getLogger(__name__)

class BaseConsumer:
    """Базовый класс для всех Kafka consumers с retry логикой"""
    
    def __init__(self, bootstrap_servers: str, topic: str, group_id: str):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.handlers: Dict[str, Callable] = {}
        self.running = False
        self.max_retries = 5
        self.retry_delay = 5  # секунд
    
    def register_handler(self, event_type: str, handler: Callable):
        """Регистрация обработчика для типа события"""
        self.handlers[event_type] = handler
    
    async def start(self):
        """Запуск consumer с retry логикой"""
        self.running = True
        retry_count = 0
        
        while self.running and retry_count < self.max_retries:
            try:
                self.consumer = AIOKafkaConsumer(
                    self.topic,
                    bootstrap_servers=self.bootstrap_servers,
                    group_id=self.group_id,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    auto_offset_reset='earliest',
                    enable_auto_commit=False,
                    max_poll_records=100,
                    session_timeout_ms=30000,
                    heartbeat_interval_ms=10000
                )
                
                await self.consumer.start()
                logger.info(f"Started consumer for topic {self.topic}")
                
                # Сброс счетчика при успешном подключении
                retry_count = 0
                
                # Основной цикл обработки сообщений
                async for msg in self.consumer:
                    if not self.running:
                        break
                    await self.process_message(msg.value)
                    await self.consumer.commit()
                    
            except Exception as e:
                retry_count += 1
                logger.error(f"Error in consumer for {self.topic}: {e}")
                logger.info(f"Retry {retry_count}/{self.max_retries} in {self.retry_delay} seconds...")
                
                if self.consumer:
                    try:
                        await self.consumer.stop()
                    except:
                        pass
                    self.consumer = None
                
                if retry_count < self.max_retries:
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(f"Max retries reached for consumer {self.topic}. Giving up.")
            finally:
                if self.consumer:
                    await self.consumer.stop()
    
    async def stop(self):
        """Остановка consumer"""
        self.running = False
        if self.consumer:
            await self.consumer.stop()
            logger.info(f"Stopped consumer for topic {self.topic}")
    
    async def process_message(self, message: Dict[str, Any]):
        """Обработка сообщения с идемпотентностью"""
        event_id = message.get('eventId')
        event_type = message.get('type')
        
        if not event_id or not event_type:
            logger.error(f"Invalid message format: {message}")
            return
        
        db = SessionLocal()
        try:
            # Проверяем дубликаты
            if IdempotencyUtils.is_event_processed(db, event_id):
                logger.info(f"Event {event_id} already processed, skipping")
                return
            
            # Вызываем соответствующий обработчик
            handler = self.handlers.get(event_type)
            if handler:
                await handler(message)
                logger.debug(f"Processed event {event_id} of type {event_type}")
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