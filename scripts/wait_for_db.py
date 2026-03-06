#!/usr/bin/env python3
import time
import psycopg2
from psycopg2 import OperationalError
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def wait_for_database():
    """Ожидание готовности PostgreSQL"""
    db_host = os.getenv("POSTGRES_HOST", "postgres")
    db_port = int(os.getenv("POSTGRES_PORT", 5432))
    db_user = os.getenv("POSTGRES_USER", "ticket_user")
    db_password = os.getenv("POSTGRES_PASSWORD", "ticket_pass")
    db_name = os.getenv("POSTGRES_DB", "ticket_db")
    
    max_retries = 30
    retry_interval = 2
    
    logger.info(f"Waiting for database at {db_host}:{db_port}...")
    
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                dbname=db_name,
                connect_timeout=5
            )
            conn.close()
            logger.info("Successfully connected to PostgreSQL!")
            return True
        except OperationalError as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries}: Database not ready. Error: {e}")
            time.sleep(retry_interval)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            time.sleep(retry_interval)
    
    logger.error("Could not connect to database after multiple attempts")
    return False

if __name__ == "__main__":
    if not wait_for_database():
        sys.exit(1)
    sys.exit(0)