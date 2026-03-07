import pytest
import requests
import json
import uuid
from typing import Dict, Any
import time
import psycopg2
import socket

# Конфигурация - для production режима!
BASE_URL = "http://localhost:8006/api/tickets"  # С префиксом /api/tickets

def is_kafka_available():
    """Проверка доступности Kafka через внешний порт 9093"""
    try:
        # Проверяем что библиотека kafka-python установлена
        from kafka import KafkaProducer
        # Проверяем что порт открыт
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('localhost', 9093))
        sock.close()
        
        if result == 0:
            print("✅ Kafka доступна на порту 9093")
            return True
        else:
            print("⚠️ Kafka порт 9093 недоступен")
            return False
    except ImportError:
        print("⚠️ Kafka библиотека не установлена")
        return False
    except Exception as e:
        print(f"⚠️ Ошибка проверки Kafka: {e}")
        return False

# Проверяем доступность Kafka
KAFKA_AVAILABLE = is_kafka_available()
print(f"📊 Kafka доступна: {KAFKA_AVAILABLE}")

@pytest.fixture(scope="session")
def base_url():
    """Базовый URL для API (с префиксом /api/tickets)"""
    return BASE_URL

@pytest.fixture(scope="session")
def kafka_available():
    return KAFKA_AVAILABLE

@pytest.fixture(scope="session")
def kafka_bootstrap_servers():
    """Адрес Kafka для тестов (с хоста)"""
    return "localhost:9093"

@pytest.fixture(scope="session")
def kafka_producer(kafka_bootstrap_servers):
    """Фикстура для Kafka producer с внешним портом 9093"""
    if not KAFKA_AVAILABLE:
        pytest.skip("Kafka not available")
    
    try:
        from kafka import KafkaProducer
        
        producer = KafkaProducer(
            bootstrap_servers=kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',
            retries=3,
            max_in_flight_requests_per_connection=5
        )
        print(f"✅ Kafka producer создан для {kafka_bootstrap_servers}")
        yield producer
        producer.close()
    except Exception as e:
        print(f"❌ Ошибка создания Kafka producer: {e}")
        pytest.skip(f"Failed to create Kafka producer: {e}")

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
        (flight_id, planned_capacity, overbook_limit, sold_total, active_total, sales_open, created_at, updated_at)
        VALUES (%s, %s, %s, 0, 0, true, NOW(), NOW())
        ON CONFLICT (flight_id) DO UPDATE SET
            sales_open = EXCLUDED.sales_open,
            updated_at = NOW()
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
        f"{BASE_URL}/v1/tickets/buy",
        json={
            "passengerId": passenger["passengerId"],
            "passengerName": passenger["passengerName"],
            "flightId": flight["flightId"],
            "isVIP": False,
            "baggageWeight": 0
        }
    )
    assert response.status_code == 201
    ticket = response.json()
    
    yield ticket, flight, passenger