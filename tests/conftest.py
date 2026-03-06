import pytest
import requests
import json
import uuid
from typing import Dict, Any
import time
import psycopg2

# Конфигурация - для production режима!
BASE_URL = "http://localhost:8006/api/tickets"  # С префиксом /api/tickets

# Пытаемся импортировать Kafka
try:
    from kafka import KafkaProducer, KafkaConsumer
    KAFKA_AVAILABLE = True
    print("✅ Kafka import successful")
except ImportError:
    KAFKA_AVAILABLE = False
    print("⚠️ Kafka not available, skipping Kafka tests")
    KafkaProducer = None
    KafkaConsumer = None

@pytest.fixture(scope="session")
def base_url():
    """Базовый URL для API (с префиксом /api/tickets)"""
    return BASE_URL

@pytest.fixture(scope="session")
def kafka_available():
    return KAFKA_AVAILABLE

@pytest.fixture(scope="session")
def kafka_producer():
    if not KAFKA_AVAILABLE:
        pytest.skip("Kafka not available")
    
    producer = KafkaProducer(
        bootstrap_servers="localhost:9092",
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    yield producer
    producer.close()

@pytest.fixture(scope="session")
def test_flight():
    flight_id = f"TEST{str(uuid.uuid4())[:8]}"
    return {
        "flightId": flight_id,
        "plannedCapacity": 100,
        "overbookLimit": 30,
        "salesOpen": True
    }

@pytest.fixture(scope="function")
def setup_test_flight(test_flight):
    """Создание тестового рейса в БД"""
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="ticket_user",
        password="ticket_pass",
        database="ticket_db"
    )
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO flight_sales 
        (flight_id, planned_capacity, overbook_limit, sold_total, active_total, sales_open, created_at)
        VALUES (%s, %s, %s, 0, 0, true, NOW())
        ON CONFLICT (flight_id) DO NOTHING
    """, (test_flight["flightId"], test_flight["plannedCapacity"], test_flight["overbookLimit"]))
    conn.commit()
    cur.close()
    conn.close()
    
    yield test_flight
    
    # Очистка
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="ticket_user",
        password="ticket_pass",
        database="ticket_db"
    )
    cur = conn.cursor()
    cur.execute("DELETE FROM tickets WHERE flight_id = %s", (test_flight["flightId"],))
    cur.execute("DELETE FROM flight_sales WHERE flight_id = %s", (test_flight["flightId"],))
    conn.commit()
    cur.close()
    conn.close()

@pytest.fixture
def test_passenger():
    return {
        "passengerId": str(uuid.uuid4()),
        "passengerName": "Тестовый Пассажир"
    }

@pytest.fixture
def test_ticket(setup_test_flight, test_passenger):
    """Создание тестового билета через API"""
    flight = setup_test_flight
    passenger = test_passenger
    
    response = requests.post(
        f"{BASE_URL}/v1/tickets/buy",  # полный путь: /api/tickets/v1/tickets/buy
        json={
            "passengerId": passenger["passengerId"],
            "passengerName": passenger["passengerName"],
            "flightId": flight["flightId"]
        }
    )
    assert response.status_code == 201
    ticket = response.json()
    
    yield ticket, flight, passenger