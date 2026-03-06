# tests/test_failure_handling.py
import requests
import uuid
from conftest import BASE_URL

def test_buy_ticket_no_flight(base_url):
    """Покупка билета на несуществующий рейс"""
    response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": str(uuid.uuid4()),
            "passengerName": "Тест",
            "flightId": "NONEXISTENT"
        }
    )
    assert response.status_code == 409
    error = response.json()
    assert error["code"] == "sales_not_initialized"
    print("✅ Error: buying on non-existent flight")

def test_buy_ticket_sold_out(base_url, setup_test_flight):
    """Покупка билета при достижении лимита"""
    flight = setup_test_flight
    
    # Заполняем рейс до лимита
    import psycopg2
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="ticket_user",
        password="ticket_pass",
        database="ticket_db"
    )
    cur = conn.cursor()
    
    limit = flight["plannedCapacity"] + flight["overbookLimit"]
    for i in range(limit):
        cur.execute("""
            INSERT INTO tickets (ticket_id, passenger_id, passenger_name, flight_id, status, created_at)
            VALUES (%s::uuid, %s::uuid, %s, %s, %s, NOW())
        """, (str(uuid.uuid4()), str(uuid.uuid4()), f"Passenger {i}", flight["flightId"], "ACTIVE"))
    
    cur.execute("""
        UPDATE flight_sales 
        SET sold_total = %s, active_total = %s
        WHERE flight_id = %s
    """, (limit, limit, flight["flightId"]))
    conn.commit()
    cur.close()
    conn.close()
    
    # Пытаемся купить еще один билет
    response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": str(uuid.uuid4()),
            "passengerName": "Тест",
            "flightId": flight["flightId"]
        }
    )
    assert response.status_code == 409
    error = response.json()
    assert error["code"] == "sold_out"
    print("✅ Error: sold out works")

def test_duplicate_ticket(base_url, setup_test_flight):
    """Покупка второго билета для того же пассажира"""
    flight = setup_test_flight
    passenger_id = str(uuid.uuid4())
    
    # Первый билет
    requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": passenger_id,
            "passengerName": "Тест",
            "flightId": flight["flightId"]
        }
    )
    
    # Второй билет (должен быть ошибка)
    response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": passenger_id,
            "passengerName": "Тест",
            "flightId": flight["flightId"]
        }
    )
    assert response.status_code == 409
    error = response.json()
    assert error["code"] == "already_has_active_ticket"
    print("✅ Error: duplicate ticket works")

def test_ticket_not_found(base_url):
    """Запрос несуществующего билета"""
    fake_id = str(uuid.uuid4())
    
    # GET by ID
    response = requests.get(f"{base_url}/v1/tickets/{fake_id}")
    assert response.status_code == 404
    
    # Refund несуществующего билета
    response = requests.post(
        f"{base_url}/v1/tickets/{fake_id}/refund",
        json={"reason": "test"}
    )
    assert response.status_code == 409
    error = response.json()
    assert error["code"] == "not_found"
    print("✅ Error: ticket not found works")