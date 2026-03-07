import requests
import uuid
from conftest import BASE_URL

def test_buy_rule_sales_open(base_url, setup_test_flight):
    """B: Проверка правила - продажа только при sales_open=true"""
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
    
    # Пытаемся купить
    response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": str(uuid.uuid4()),
            "passengerName": "Rule Test",
            "flightId": flight["flightId"]
        }
    )
    assert response.status_code == 409
    assert response.json()["code"] == "sales_closed"
    print("✅ Buy rule: sales must be open")

def test_buy_rule_limit(base_url, setup_test_flight):
    """B: Проверка правила - лимит продаж"""
    flight = setup_test_flight
    limit = flight["plannedCapacity"] + flight["overbookLimit"]
    
    # Заполняем до лимита
    for i in range(limit):
        requests.post(
            f"{base_url}/v1/tickets/buy",
            json={
                "passengerId": str(uuid.uuid4()),
                "passengerName": f"Limit Test {i}",
                "flightId": flight["flightId"]
            }
        )
    
    # Пытаемся купить еще один
    response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": str(uuid.uuid4()),
            "passengerName": "Over Limit Test",
            "flightId": flight["flightId"]
        }
    )
    assert response.status_code == 409
    assert response.json()["code"] == "sold_out"
    print("✅ Buy rule: limit check works")

def test_refund_rule_active_only(base_url, setup_test_flight):
    """B: Проверка правила - возврат только active билетов"""
    flight = setup_test_flight
    passenger_id = str(uuid.uuid4())
    
    # Покупаем билет
    buy_response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": passenger_id,
            "passengerName": "Refund Rule Test",
            "flightId": flight["flightId"]
        }
    )
    ticket = buy_response.json()
    
    # Возвращаем
    refund_response = requests.post(
        f"{base_url}/v1/tickets/{ticket['ticketId']}/refund",
        json={"reason": "test"}
    )
    assert refund_response.status_code == 200
    
    # Пытаемся вернуть еще раз
    second_refund = requests.post(
        f"{base_url}/v1/tickets/{ticket['ticketId']}/refund",
        json={"reason": "test again"}
    )
    assert second_refund.status_code == 409
    assert "Only active tickets can be refunded" in second_refund.json()["message"]
    print("✅ Refund rule: only active tickets can be refunded")

def test_refund_rule_sales_open(base_url, setup_test_flight):
    """B: Проверка правила - возврат только при открытых продажах"""
    flight = setup_test_flight
    passenger_id = str(uuid.uuid4())
    
    # Покупаем билет
    buy_response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": passenger_id,
            "passengerName": "Refund Sales Rule",
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
    refund_response = requests.post(
        f"{base_url}/v1/tickets/{ticket['ticketId']}/refund",
        json={"reason": "test"}
    )
    assert refund_response.status_code == 409
    assert refund_response.json()["code"] == "refund_closed"
    print("✅ Refund rule: sales must be open")