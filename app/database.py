# app/database.py
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# PostgreSQL engine с пулом соединений
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.debug
)

# Фабрика сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для моделей
Base = declarative_base()

# Зависимость для FastAPI
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Проверка соединения с БД - ИСПРАВЛЕНО
def check_database_connection():
    try:
        with engine.connect() as conn:
            # Используем text() для raw SQL
            conn.execute(text("SELECT 1"))
            conn.commit()
        logger.info("Successfully connected to PostgreSQL")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        return False