import requests
import uuid
from conftest import BASE_URL

def test_ticket_status_active(base_url, setup_test_flight):
    """B: Проверка статуса active"""
    flight = setup_test_flight
    passenger_id = str(uuid.uuid4())
    
    response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": passenger_id,
            "passengerName": "Active Test",
            "flightId": flight["flightId"]
        }
    )
    assert response.status_code == 201
    ticket = response.json()
    assert ticket["status"] == "active"
    print("✅ Status 'active' works")

def test_ticket_status_returned(base_url, setup_test_flight):
    """B: Проверка статуса returned"""
    flight = setup_test_flight
    passenger_id = str(uuid.uuid4())
    
    buy_response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": passenger_id,
            "passengerName": "Returned Test",
            "flightId": flight["flightId"]
        }
    )
    ticket = buy_response.json()
    
    refund_response = requests.post(
        f"{base_url}/v1/tickets/{ticket['ticketId']}/refund",
        json={"reason": "test"}
    )
    assert refund_response.status_code == 200
    refunded = refund_response.json()
    assert refunded["status"] == "returned"
    print("✅ Status 'returned' works")

def test_ticket_status_bumped(base_url, setup_test_flight):
    """B: Проверка статуса bumped"""
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
    ticket = buy_response.json()
    
    # Напрямую в БД меняем статус на bumped (имитация overbooking)
    import psycopg2
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="ticket_user",
        password="ticket_pass",
        database="ticket_db"
    )
    cur = conn.cursor()
    cur.execute(
        "UPDATE tickets SET status = 'BUMPED' WHERE ticket_id = %s",
        (ticket["ticketId"],)
    )
    conn.commit()
    cur.close()
    conn.close()
    
    # Проверяем статус
    response = requests.get(f"{base_url}/v1/tickets/{ticket['ticketId']}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "bumped"
    print("✅ Status 'bumped' works")

# tests/test_status_flows.py (только функция test_ticket_status_fake)
def test_ticket_status_fake(base_url, setup_test_flight):
    """B: Проверка статуса fake (можно создать через прямой SQL)"""
    flight = setup_test_flight
    ticket_id = str(uuid.uuid4())
    passenger_id = str(uuid.uuid4())
    
    # Создаем fake билет напрямую в БД
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
        INSERT INTO tickets (
            ticket_id, passenger_id, passenger_name, flight_id, status, 
            is_vip, baggage_weight, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, NOW(), NOW()
        )
    """, (ticket_id, passenger_id, "Fake Passenger", flight["flightId"], "FAKE", False, 0))
    conn.commit()
    cur.close()
    conn.close()
    
    # Проверяем через API
    response = requests.get(f"{base_url}/v1/tickets/{ticket_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "fake"
    print("✅ Status 'fake' works")