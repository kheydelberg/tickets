import requests
import uuid
from conftest import BASE_URL

def test_sold_total_counter(base_url, setup_test_flight):
    """B: Проверка счетчика sold_total"""
    flight = setup_test_flight
    initial_sales = requests.get(f"{base_url}/v1/flight-sales/{flight['flightId']}").json()
    initial_sold = initial_sales["soldTotal"]
    
    # Покупаем билет
    requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": str(uuid.uuid4()),
            "passengerName": "Counter Test",
            "flightId": flight["flightId"]
        }
    )
    
    # Проверяем увеличение sold_total
    sales = requests.get(f"{base_url}/v1/flight-sales/{flight['flightId']}").json()
    assert sales["soldTotal"] == initial_sold + 1
    print("✅ sold_total counter increments on buy")

def test_active_total_counter(base_url, setup_test_flight):
    """B: Проверка счетчика active_total"""
    flight = setup_test_flight
    initial_sales = requests.get(f"{base_url}/v1/flight-sales/{flight['flightId']}").json()
    initial_active = initial_sales["activeTotal"]
    
    # Покупаем билет
    buy_response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": str(uuid.uuid4()),
            "passengerName": "Active Counter Test",
            "flightId": flight["flightId"]
        }
    )
    ticket = buy_response.json()
    
    # Проверяем увеличение active_total
    sales_after_buy = requests.get(f"{base_url}/v1/flight-sales/{flight['flightId']}").json()
    assert sales_after_buy["activeTotal"] == initial_active + 1
    
    # Возвращаем билет
    requests.post(
        f"{base_url}/v1/tickets/{ticket['ticketId']}/refund",
        json={"reason": "test"}
    )
    
    # Проверяем уменьшение active_total
    sales_after_refund = requests.get(f"{base_url}/v1/flight-sales/{flight['flightId']}").json()
    assert sales_after_refund["activeTotal"] == initial_active
    print("✅ active_total counter works correctly")

def test_sales_open_flag(base_url, setup_test_flight):
    """B: Проверка флага sales_open"""
    flight = setup_test_flight
    
    # Проверяем что продажи открыты
    sales = requests.get(f"{base_url}/v1/flight-sales/{flight['flightId']}").json()
    assert sales["salesOpen"] == True
    
    # Закрываем продажи напрямую в БД
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
            "passengerName": "Closed Sales Test",
            "flightId": flight["flightId"]
        }
    )
    assert response.status_code == 409
    error = response.json()
    assert error["code"] == "sales_closed"
    print("✅ sales_open flag works")