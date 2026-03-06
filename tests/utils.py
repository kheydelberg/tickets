# tests/utils.py
import psycopg2
import uuid
from typing import Dict, Any

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "ticket_user",
    "password": "ticket_pass",
    "database": "ticket_db"
}

def create_test_flight(flight_id: str = None, capacity: int = 100) -> str:
    """Создание тестового рейса в БД"""
    if flight_id is None:
        flight_id = f"TEST{str(uuid.uuid4())[:8]}"
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO flight_sales 
        (flight_id, planned_capacity, overbook_limit, sold_total, active_total, sales_open, created_at)
        VALUES (%s, %s, %s, 0, 0, true, NOW())
        ON CONFLICT (flight_id) DO NOTHING
    """, (flight_id, capacity, int(capacity * 0.3)))
    conn.commit()
    cur.close()
    conn.close()
    return flight_id

def create_test_ticket(flight_id: str, passenger_id: str = None) -> Dict[str, Any]:
    """Создание тестового билета напрямую в БД"""
    if passenger_id is None:
        passenger_id = str(uuid.uuid4())
    
    ticket_id = str(uuid.uuid4())
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tickets (ticket_id, passenger_id, passenger_name, flight_id, status, created_at)
        VALUES (%s::uuid, %s::uuid, %s, %s, %s, NOW())
    """, (ticket_id, passenger_id, "Test Passenger", flight_id, "ACTIVE"))
    
    cur.execute("""
        UPDATE flight_sales 
        SET sold_total = sold_total + 1, active_total = active_total + 1
        WHERE flight_id = %s
    """, (flight_id,))
    conn.commit()
    cur.close()
    conn.close()
    
    return {
        "ticketId": ticket_id,
        "passengerId": passenger_id,
        "flightId": flight_id
    }

def cleanup_test_data(flight_id: str):
    """Очистка тестовых данных"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("DELETE FROM tickets WHERE flight_id = %s", (flight_id,))
    cur.execute("DELETE FROM flight_sales WHERE flight_id = %s", (flight_id,))
    conn.commit()
    cur.close()
    conn.close()

def get_flight_sales(flight_id: str) -> Dict[str, Any]:
    """Получение данных о продажах из БД"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT * FROM flight_sales WHERE flight_id = %s", (flight_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if row:
        return {
            "flightId": row[0],
            "plannedCapacity": row[1],
            "overbookLimit": row[2],
            "soldTotal": row[3],
            "activeTotal": row[4],
            "salesOpen": row[5]
        }
    return None