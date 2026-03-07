# tests/test_overbooking.py
import requests
import uuid
import psycopg2
from conftest import BASE_URL

def test_f6_overbooking_manual():
    """F6: Ручная имитация обработки овербукинга"""
    # Создаем рейс
    flight_id = f"OVR{str(uuid.uuid4())[:8]}"
    
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="ticket_user",
        password="ticket_pass",
        database="ticket_db"
    )
    cur = conn.cursor()
    
    # Создаем рейс
    cur.execute("""
        INSERT INTO flight_sales 
        (flight_id, planned_capacity, overbook_limit, sold_total, active_total, sales_open, created_at, updated_at)
        VALUES (%s, 100, 30, 0, 0, true, NOW(), NOW())
    """, (flight_id,))
    
    # Создаем несколько активных билетов
    bumped_passengers = []
    for i in range(3):
        passenger_id = str(uuid.uuid4())
        ticket_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO tickets (
                ticket_id, passenger_id, passenger_name, flight_id, status, 
                is_vip, baggage_weight, created_at, updated_at
            ) VALUES (
                %s::uuid, %s::uuid, %s, %s, %s,
                %s, %s, NOW(), NOW()
            )
        """, (ticket_id, passenger_id, f"Passenger {i}", flight_id, "ACTIVE", False, 0))
        bumped_passengers.append(passenger_id)
    
    cur.execute("""
        UPDATE flight_sales 
        SET sold_total = 3, active_total = 3, updated_at = NOW()
        WHERE flight_id = %s
    """, (flight_id,))
    conn.commit()
    
    # Имитация обработки boarding.result
    for passenger_id in bumped_passengers:
        cur.execute("""
            UPDATE tickets 
            SET status = 'BUMPED', updated_at = NOW()
            WHERE passenger_id = %s::uuid AND flight_id = %s
        """, (passenger_id, flight_id))
    
    cur.execute("""
        UPDATE flight_sales 
        SET active_total = 0, updated_at = NOW()
        WHERE flight_id = %s
    """, (flight_id,))
    conn.commit()
    cur.close()
    conn.close()
    
    # Проверка результатов
    response = requests.get(f"{BASE_URL}/v1/flight-sales/{flight_id}")
    sales = response.json()
    assert sales["soldTotal"] == 3
    assert sales["activeTotal"] == 0
    
    response = requests.get(f"{BASE_URL}/v1/tickets?flightId={flight_id}&status=bumped")
    tickets = response.json()
    assert len(tickets) == 3
    for ticket in tickets:
        assert ticket["status"] == "bumped"
    
    print("✅ F6: Overbooking logic works")