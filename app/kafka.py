# app/kafka.py
import json
import logging
from typing import Optional
from aiokafka import AIOKafkaProducer
from app.config import settings
from app.utils.json_encoder import CustomJSONEncoder

logger = logging.getLogger(__name__)

class KafkaProducerWrapper:
    """Обертка для Kafka Producer с синглтоном"""
    _instance: Optional[AIOKafkaProducer] = None
    
    @classmethod
    async def get_instance(cls) -> AIOKafkaProducer:
        if cls._instance is None:
            try:
                cls._instance = AIOKafkaProducer(
                    bootstrap_servers=settings.kafka_bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v, cls=CustomJSONEncoder).encode('utf-8'),
                    max_request_size=1048576,
                    request_timeout_ms=40000
                )
                await cls._instance.start()
                logger.info("Kafka producer started successfully")
            except Exception as e:
                logger.error(f"Failed to start Kafka producer: {e}")
                cls._instance = None
                raise
        return cls._instance
    
    @classmethod
    async def close_instance(cls):
        if cls._instance:
            await cls._instance.stop()
            cls._instance = None
            logger.info("Kafka producer stopped")

# Функция для получения producer
async def get_kafka_producer() -> Optional[AIOKafkaProducer]:
    try:
        return await KafkaProducerWrapper.get_instance()
    except Exception as e:
        logger.error(f"Error getting Kafka producer: {e}")
        return None