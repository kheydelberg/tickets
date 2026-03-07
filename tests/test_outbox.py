import pytest
import requests
import uuid
import time
import json
from conftest import BASE_URL

def test_outbox_created_on_buy(base_url, setup_test_flight):
    """Проверка создания записи в outbox при покупке"""
    flight = setup_test_flight
    passenger_id = str(uuid.uuid4())
    
    # Покупаем билет
    response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": passenger_id,
            "passengerName": "Outbox Test",
            "flightId": flight["flightId"]
        }
    )
    assert response.status_code == 201
    ticket = response.json()
    
    # Проверяем outbox в БД
    import psycopg2
    import json
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="ticket_user",
        password="ticket_pass",
        database="ticket_db"
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT topic, key, value, status 
        FROM outbox_messages 
        WHERE key = %s
        ORDER BY created_at DESC
    """, (ticket["ticketId"],))
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    assert row is not None
    topic, key, value_json, status = row
    
    assert topic == "tickets.events"
    assert key == ticket["ticketId"]
    assert status == "pending"
    
    value = value_json if isinstance(value_json, dict) else json.loads(value_json)
    assert value["type"] == "ticket.bought"
    assert value["producer"] == "tickets"
    assert value["payload"]["ticketId"] == ticket["ticketId"]
    assert value["payload"]["passengerId"] == passenger_id
    print("✅ Outbox record created on buy")

def test_outbox_created_on_refund(base_url, setup_test_flight):
    """Проверка создания записи в outbox при возврате"""
    flight = setup_test_flight
    passenger_id = str(uuid.uuid4())
    
    # Покупаем билет
    buy_response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": passenger_id,
            "passengerName": "Outbox Refund Test",
            "flightId": flight["flightId"]
        }
    )
    ticket = buy_response.json()
    
    # Возвращаем билет
    refund_response = requests.post(
        f"{base_url}/v1/tickets/{ticket['ticketId']}/refund",
        json={"reason": "outbox_test"}
    )
    assert refund_response.status_code == 200
    
    # Проверяем outbox в БД
    import psycopg2
    import json
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="ticket_user",
        password="ticket_pass",
        database="ticket_db"
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT topic, value, status 
        FROM outbox_messages 
        WHERE key = %s AND topic = 'tickets.events'
        ORDER BY created_at DESC
    """, (ticket["ticketId"],))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    # Должно быть два сообщения: bought и refunded
    assert len(rows) >= 2
    
    # Проверяем последнее сообщение (refunded)
    topic, value_json, status = rows[0]
    value = value_json if isinstance(value_json, dict) else json.loads(value_json)
    assert value["type"] == "ticket.refunded"
    assert value["payload"]["ticketId"] == ticket["ticketId"]
    assert value["payload"]["reason"] == "outbox_test"
    print("✅ Outbox record created on refund")

def test_outbox_message_format(base_url, setup_test_flight):
    """Проверка формата сообщения в outbox"""
    flight = setup_test_flight
    passenger_id = str(uuid.uuid4())
    
    # Покупаем билет
    response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": passenger_id,
            "passengerName": "Format Test",
            "flightId": flight["flightId"]
        }
    )
    ticket = response.json()
    
    # Проверяем outbox
    import psycopg2
    import json
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
        WHERE key = %s
        ORDER BY created_at DESC
    """, (ticket["ticketId"],))
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    value = row[0] if isinstance(row[0], dict) else json.loads(row[0])
    
    # Проверяем формат Envelope
    assert "eventId" in value
    assert "type" in value
    assert "ts" in value
    assert "producer" in value
    assert "entity" in value
    assert "payload" in value
    
    assert value["producer"] == "tickets"
    assert value["type"] == "ticket.bought"
    assert value["entity"]["kind"] == "ticket"
    assert value["entity"]["id"] == ticket["ticketId"]
    print("✅ Outbox message follows Envelope format")

def test_outbox_status_pending(base_url, setup_test_flight):
    """Проверка статуса pending в outbox"""
    flight = setup_test_flight
    passenger_id = str(uuid.uuid4())
    
    # Покупаем билет
    response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": passenger_id,
            "passengerName": "Status Test",
            "flightId": flight["flightId"]
        }
    )
    ticket = response.json()
    
    # Проверяем статус
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
        SELECT status FROM outbox_messages 
        WHERE key = %s
    """, (ticket["ticketId"],))
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    assert row[0] == "pending"
    print("✅ Outbox status is pending")