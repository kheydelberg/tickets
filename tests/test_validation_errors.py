import requests
import uuid
from conftest import BASE_URL

def test_validation_error_missing_flight_id(base_url):
    """400: flightId is required"""
    response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": str(uuid.uuid4()),
            "passengerName": "Test User"
            # Нет flightId
        }
    )
    assert response.status_code == 400
    error = response.json()
    assert error["code"] == "validation_error"
    print("✅ 400 Validation Error: missing flightId")

def test_not_found_error_ticket(base_url):
    """404: Ticket not found"""
    fake_id = str(uuid.uuid4())
    response = requests.get(f"{base_url}/v1/tickets/{fake_id}")
    assert response.status_code == 404
    error = response.json()
    assert error["code"] == "not_found"
    print("✅ 404 Not Found: ticket")

def test_not_found_error_flight_sales(base_url):
    """404: Flight sales not found"""
    fake_flight = f"FAKE{str(uuid.uuid4())[:8]}"
    response = requests.get(f"{base_url}/v1/flight-sales/{fake_flight}")
    assert response.status_code == 404
    error = response.json()
    assert error["code"] == "not_found"
    print("✅ 404 Not Found: flight sales")

def test_conflict_sales_closed(base_url, setup_test_flight):
    """409: Sales are closed"""
    flight = setup_test_flight
    
    # Закрываем продажи
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
        "UPDATE flight_sales SET sales_open = false WHERE flight_id = %s",
        (flight["flightId"],)
    )
    conn.commit()
    cur.close()
    conn.close()
    
    # Пытаемся купить билет
    response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": str(uuid.uuid4()),
            "passengerName": "Test",
            "flightId": flight["flightId"]
        }
    )
    assert response.status_code == 409
    error = response.json()
    assert error["code"] == "sales_closed"
    print("✅ 409 Conflict: sales closed")

def test_conflict_sold_out(base_url, setup_test_flight):
    """409: Sold out (limit reached)"""
    flight = setup_test_flight
    limit = flight["plannedCapacity"] + flight["overbookLimit"]
    
    # Заполняем до лимита
    for i in range(limit):
        requests.post(
            f"{base_url}/v1/tickets/buy",
            json={
                "passengerId": str(uuid.uuid4()),
                "passengerName": f"User {i}",
                "flightId": flight["flightId"]
            }
        )
    
    # Пытаемся купить еще один
    response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": str(uuid.uuid4()),
            "passengerName": "Over Limit",
            "flightId": flight["flightId"]
        }
    )
    assert response.status_code == 409
    error = response.json()
    assert error["code"] == "sold_out"
    print("✅ 409 Conflict: sold out")

def test_conflict_already_has_active_ticket(base_url, setup_test_flight):
    """409: Passenger already has active ticket"""
    flight = setup_test_flight
    passenger_id = str(uuid.uuid4())
    
    # Первый билет
    requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": passenger_id,
            "passengerName": "Test",
            "flightId": flight["flightId"]
        }
    )
    
    # Второй билет (должен быть конфликт)
    response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": passenger_id,
            "passengerName": "Test",
            "flightId": flight["flightId"]
        }
    )
    assert response.status_code == 409
    error = response.json()
    assert error["code"] == "already_has_active_ticket"
    print("✅ 409 Conflict: already has active ticket")

def test_conflict_refund_closed(base_url, setup_test_flight):
    """409: Refund not allowed after sales closed"""
    flight = setup_test_flight
    passenger_id = str(uuid.uuid4())
    
    # Покупаем билет
    buy_response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": passenger_id,
            "passengerName": "Test",
            "flightId": flight["flightId"]
        }
    )
    ticket = buy_response.json()
    
    # Закрываем продажи
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
        "UPDATE flight_sales SET sales_open = false WHERE flight_id = %s",
        (flight["flightId"],)
    )
    conn.commit()
    cur.close()
    conn.close()
    
    # Пытаемся вернуть
    response = requests.post(
        f"{base_url}/v1/tickets/{ticket['ticketId']}/refund",
        json={"reason": "test"}
    )
    assert response.status_code == 409
    error = response.json()
    assert error["code"] == "refund_closed"
    print("✅ 409 Conflict: refund closed")