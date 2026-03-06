from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from app.config import settings
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class KafkaProducerWrapper:
    """Обертка для Kafka Producer с синглтоном"""
    _instance: Optional[AIOKafkaProducer] = None
    
    @classmethod
    async def get_instance(cls) -> AIOKafkaProducer:
        if cls._instance is None:
            cls._instance = AIOKafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            await cls._instance.start()
            logger.info("Kafka producer started")
        return cls._instance
    
    @classmethod
    async def close_instance(cls):
        if cls._instance:
            await cls._instance.stop()
            cls._instance = None
            logger.info("Kafka producer stopped")

# Функция для получения producer
async def get_kafka_producer() -> AIOKafkaProducer:
    return await KafkaProducerWrapper.get_instance()