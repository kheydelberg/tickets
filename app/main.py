from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, check_database_connection
from app.api.v1.endpoints import tickets, sales
from app.api.v1 import errors  # Импортируем обработчики ошибок
from app.config import settings
from app.kafka import KafkaProducerWrapper
from app.consumers.flight_consumer import FlightConsumer
from app.consumers.passenger_consumer import PassengerConsumer
from app.consumers.boarding_consumer import BoardingConsumer
import asyncio
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Создание таблиц
logger.info("Creating database tables...")
Base.metadata.create_all(bind=engine)

# Проверка подключения к БД
if not check_database_connection():
    logger.error("Failed to connect to database")
    exit(1)

# Создание FastAPI приложения
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Ticket Sales Service for Airport Simulation"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(tickets.router, prefix="/api/tickets" if settings.environment == "production" else "")
app.include_router(sales.router, prefix="/api/tickets" if settings.environment == "production" else "")

# Фоновые задачи
consumers = []

@app.on_event("startup")
async def startup_event():
    """Запуск при старте"""
    logger.info("Starting Ticket Sales Service...")
    
    # Запускаем Kafka consumers
    flight_consumer = FlightConsumer()
    passenger_consumer = PassengerConsumer()
    boarding_consumer = BoardingConsumer()
    
    consumers.extend([flight_consumer, passenger_consumer, boarding_consumer])
    
    # Запускаем каждого consumer в отдельной задаче
    for consumer in consumers:
        asyncio.create_task(consumer.start())
        logger.info(f"Started consumer for {consumer.topic}")

@app.on_event("shutdown")
async def shutdown_event():
    """Остановка при завершении"""
    logger.info("Shutting down Ticket Sales Service...")
    await KafkaProducerWrapper.close_instance()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment
    }