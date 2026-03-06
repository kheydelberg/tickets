from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text  # НЕ ЗАБУДЬ ЭТОТ ИМПОРТ!
from app.database import engine, Base, check_database_connection, SessionLocal
from app.api.v1.endpoints import tickets, sales
from app.api.v1.errors import (
    validation_exception_handler,
    value_error_handler,
    general_exception_handler
)
from app.config import settings
import logging
import asyncio

# Настройка логирования
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Создание FastAPI приложения ДО проверки БД
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Ticket Sales Service for Airport Simulation"
)

# Регистрация обработчиков ошибок
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(ValueError, value_error_handler)
app.add_exception_handler(Exception, general_exception_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры - префикс /api/tickets добавляется только в production
app.include_router(tickets.router, prefix="/api/tickets" if settings.environment == "production" else "")
app.include_router(sales.router, prefix="/api/tickets" if settings.environment == "production" else "")

# Проверка подключения к БД при старте
@app.on_event("startup")
async def startup_event():
    """Запуск при старте"""
    logger.info("Starting Ticket Sales Service...")
    
    # Создание таблиц
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Проверка подключения к БД
    if not check_database_connection():
        logger.error("Failed to connect to database")
        logger.warning("Service will continue but database operations may fail")
    
    # Запускаем Kafka consumers в фоне без ожидания
    asyncio.create_task(start_consumers())

async def start_consumers():
    """Запуск всех consumers в фоне"""
    try:
        from app.kafka import KafkaProducerWrapper
        from app.consumers.flight_consumer import FlightConsumer
        from app.consumers.passenger_consumer import PassengerConsumer
        from app.consumers.boarding_consumer import BoardingConsumer
        
        # Даем Kafka время на запуск
        logger.info("Waiting 10 seconds for Kafka to be ready...")
        await asyncio.sleep(10)
        
        flight_consumer = FlightConsumer()
        passenger_consumer = PassengerConsumer()
        boarding_consumer = BoardingConsumer()
        
        consumers = [flight_consumer, passenger_consumer, boarding_consumer]
        
        # Запускаем каждого consumer в отдельной задаче
        for consumer in consumers:
            asyncio.create_task(consumer.start())
            logger.info(f"Started background task for {consumer.topic}")
            
    except Exception as e:
        logger.warning(f"Failed to start Kafka consumers: {e}")
        logger.warning("Service will continue without Kafka (manual operations only)")

@app.on_event("shutdown")
async def shutdown_event():
    """Остановка при завершении"""
    logger.info("Shutting down Ticket Sales Service...")
    try:
        from app.kafka import KafkaProducerWrapper
        await KafkaProducerWrapper.close_instance()
    except:
        pass

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Проверяем БД
    db_status = "disconnected"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "connected"
    except:
        pass
    
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
        "database": db_status
    }