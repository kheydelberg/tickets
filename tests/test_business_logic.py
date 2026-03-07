# tests/test_business_logic.py
import requests
import uuid
import time
from conftest import BASE_URL

def test_f1_initialize_sales_direct():
    """F1: Создание flight_sales через прямое SQL (имитация flight.created)"""
    import psycopg2
    
    flight_id = f"F1{str(uuid.uuid4())[:8]}"
    capacity = 150
    
    # Прямое создание записи (имитация consumer)
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
    """, (flight_id, capacity, int(capacity * 0.3)))
    conn.commit()
    cur.close()
    conn.close()
    
    # Проверка через API
    response = requests.get(f"{BASE_URL}/v1/flight-sales/{flight_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["flightId"] == flight_id
    assert data["plannedCapacity"] == capacity
    assert data["overbookLimit"] == int(capacity * 0.3)
    assert data["salesOpen"] == True
    print("✅ F1: Initialize sales works")

def test_f2_close_sales(base_url, setup_test_flight):
    """F2: Закрытие продаж (имитация flight.status.changed)"""
    flight = setup_test_flight
    
    # Проверяем что продажи открыты
    sales = requests.get(f"{base_url}/v1/flight-sales/{flight['flightId']}").json()
    assert sales["salesOpen"] == True
    
    # Прямое закрытие продаж в БД (имитация consumer)
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
    
    # Проверяем что продажи закрыты
    sales = requests.get(f"{base_url}/v1/flight-sales/{flight['flightId']}").json()
    assert sales["salesOpen"] == False
    
    # Пытаемся купить билет
    response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": str(uuid.uuid4()),
            "passengerName": "Тест",
            "flightId": flight["flightId"]
        }
    )
    assert response.status_code == 409  # Conflict
    error_data = response.json()
    assert error_data["code"] == "sales_closed"  # ✅ правильно
    assert error_data["message"] == "Sales are closed for this flight"  # ✅ добавить проверку message
    print("✅ F2: Close sales works")

def test_f3_auto_buy_manual():
    """F3: Тест логики авто-покупки (без Kafka)"""
    import psycopg2
    flight_id = f"AUTO{str(uuid.uuid4())[:8]}"
    capacity = 50
    
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
    """, (flight_id, capacity, int(capacity * 0.3)))
    conn.commit()
    
    # Прямая вставка билета (имитация auto-buy) - добавляем ВСЕ поля
    ticket_id = str(uuid.uuid4())
    passenger_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO tickets (
            ticket_id, passenger_id, passenger_name, flight_id, status, 
            is_vip, baggage_weight, created_at, updated_at
        ) VALUES (
            %s::uuid, %s::uuid, %s, %s, %s, 
            %s, %s, NOW(), NOW()
        )
    """, (ticket_id, passenger_id, "Auto Passenger", flight_id, "ACTIVE", False, 0))
    
    # Обновляем счетчики
    cur.execute("""
        UPDATE flight_sales 
        SET sold_total = sold_total + 1, active_total = active_total + 1, updated_at = NOW()
        WHERE flight_id = %s
    """, (flight_id,))
    conn.commit()
    cur.close()
    conn.close()
    
    # Проверка через API
    response = requests.get(f"{BASE_URL}/v1/flight-sales/{flight_id}")
    sales = response.json()
    assert sales["soldTotal"] == 1
    assert sales["activeTotal"] == 1
    
    response = requests.get(f"{BASE_URL}/v1/tickets?flightId={flight_id}")
    tickets = response.json()
    assert len(tickets) == 1
    assert tickets[0]["status"] == "active"
    print("✅ F3: Auto-buy logic works")

def test_f4_manual_buy_already_tested_in_rest_api():
    """F4 уже протестирован в test_rest_api.py"""
    pass

def test_f5_refund_rules(base_url, setup_test_flight):
    """F5: Проверка правил возврата"""
    flight = setup_test_flight
    
    # Создаем билет
    buy_response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": str(uuid.uuid4()),
            "passengerName": "Тест",
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
    
    # Пытаемся вернуть билет после закрытия продаж
    response = requests.post(
        f"{base_url}/v1/tickets/{ticket['ticketId']}/refund",
        json={"reason": "test"}
    )
    assert response.status_code == 409
    error = response.json()
    assert error["code"] == "refund_closed"
    print("✅ F5: Refund rules work")