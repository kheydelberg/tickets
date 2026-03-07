import pytest
import json
import time
import uuid
from conftest import BASE_URL, KAFKA_AVAILABLE
import requests

pytestmark = pytest.mark.skipif(not KAFKA_AVAILABLE, reason="Kafka not available")

def test_produce_ticket_bought(setup_test_flight, base_url, kafka_producer):
    """Проверка публикации ticket.bought при покупке билета"""
    flight = setup_test_flight
    passenger_id = str(uuid.uuid4())
    
    # Покупаем билет
    response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": passenger_id,
            "passengerName": "Producer Test",
            "flightId": flight["flightId"]
        }
    )
    assert response.status_code == 201
    
    # Проверяем outbox (нужно подключиться к БД)
    import psycopg2
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="ticket_user",
        password="ticket_pass",
        database="ticket_db"
    )
    cur = conn.cursor()
    cur.execute("SELECT * FROM outbox_messages WHERE topic = 'tickets.events' ORDER BY created_at DESC LIMIT 1")
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    assert row is not None
    message = row[3]  # value column
    assert message["type"] == "ticket.bought"
    assert message["producer"] == "tickets"
    assert message["payload"]["passengerId"] == passenger_id
    print("✅ ticket.bought event created in outbox")

def test_produce_ticket_refunded(setup_test_flight, base_url):
    """Проверка публикации ticket.refunded при возврате билета"""
    flight = setup_test_flight
    passenger_id = str(uuid.uuid4())
    
    # Покупаем билет
    buy_response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": passenger_id,
            "passengerName": "Refund Test",
            "flightId": flight["flightId"]
        }
    )
    ticket = buy_response.json()
    
    # Возвращаем билет
    refund_response = requests.post(
        f"{base_url}/v1/tickets/{ticket['ticketId']}/refund",
        json={"reason": "test_producer"}
    )
    assert refund_response.status_code == 200
    
    # Проверяем outbox
    import psycopg2
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="ticket_user",
        password="ticket_pass",
        database="ticket_db"
    )
    cur = conn.cursor()
    cur.execute("SELECT * FROM outbox_messages WHERE topic = 'tickets.events' ORDER BY created_at DESC LIMIT 1")
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    assert row is not None
    message = row[3]
    assert message["type"] == "ticket.refunded"
    assert message["payload"]["ticketId"] == ticket['ticketId']
    assert message["payload"]["reason"] == "test_producer"
    print("✅ ticket.refunded event created in outbox")

def test_produce_ticket_bumped(setup_test_flight, base_url, kafka_producer):
    """Проверка публикации ticket.bumped при овербукинге"""
    flight = setup_test_flight
    passenger_id = str(uuid.uuid4())
    
    # Создаем билет
    buy_response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": passenger_id,
            "passengerName": "Bumped Test",
            "flightId": flight["flightId"]
        }
    )
    assert buy_response.status_code == 201
    
    # Отправляем событие овербукинга
    event = {
        "eventId": str(uuid.uuid4()),
        "type": "board.boarding.result",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "producer": "boarding",
        "entity": {"kind": "flight", "id": flight["flightId"]},
        "payload": {
            "flightId": flight["flightId"],
            "boardedPassengerIds": [],
            "bumpedPassengerIds": [passenger_id]
        }
    }
    
    future = kafka_producer.send('board.events', value=event)
    future.get(timeout=10)
    
    # Ждем обработки
    time.sleep(2)
    
    # Проверяем outbox на наличие bumped события
    import psycopg2
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="ticket_user",
        password="ticket_pass",
        database="ticket_db"
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT value FROM outbox_messages 
        WHERE topic = 'tickets.events' 
        ORDER BY created_at DESC 
        LIMIT 1
    """)
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    assert row is not None
    message = row[0]
    assert message["type"] == "ticket.bumped"
    assert message["payload"]["passengerId"] == passenger_id
    print("✅ ticket.bumped event created in outbox")