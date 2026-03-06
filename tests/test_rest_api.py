# tests/test_rest_api.py
import requests
import uuid
from conftest import BASE_URL

def test_get_flight_sales(base_url, setup_test_flight):
    """C1: GET /v1/flight-sales/{flightId}"""
    flight = setup_test_flight
    response = requests.get(f"{base_url}/v1/flight-sales/{flight['flightId']}")
    assert response.status_code == 200
    data = response.json()
    assert data["flightId"] == flight["flightId"]
    assert data["plannedCapacity"] == flight["plannedCapacity"]
    assert data["overbookLimit"] == flight["overbookLimit"]
    assert data["soldTotal"] == 0
    assert data["activeTotal"] == 0
    assert data["salesOpen"] == True
    print("✅ GET /flight-sales works")

def test_buy_ticket_manual(base_url, setup_test_flight):
    """F4: POST /v1/tickets/buy - ручная покупка"""
    flight = setup_test_flight
    passenger_id = str(uuid.uuid4())
    
    response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": passenger_id,
            "passengerName": "Иван Петров",
            "flightId": flight["flightId"]
        }
    )
    assert response.status_code == 201
    ticket = response.json()
    assert ticket["passengerId"] == passenger_id
    assert ticket["flightId"] == flight["flightId"]
    assert ticket["status"] == "active"
    assert "ticketId" in ticket
    print("✅ Manual buy works")

def test_get_tickets(base_url, setup_test_flight):
    """C1: GET /v1/tickets с фильтрацией"""
    flight = setup_test_flight
    
    # Создаем билет
    passenger_id = str(uuid.uuid4())
    buy_response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": passenger_id,
            "passengerName": "Тест",
            "flightId": flight["flightId"]
        }
    )
    ticket = buy_response.json()
    
    # Проверяем GET /v1/tickets
    response = requests.get(f"{base_url}/v1/tickets")
    assert response.status_code == 200
    tickets = response.json()
    assert len(tickets) >= 1
    
    # Проверка фильтра по flightId
    response = requests.get(f"{base_url}/v1/tickets?flightId={flight['flightId']}")
    assert response.status_code == 200
    tickets = response.json()
    assert len(tickets) >= 1
    assert tickets[0]["flightId"] == flight["flightId"]
    
    # Проверка фильтра по passengerId
    response = requests.get(f"{base_url}/v1/tickets?passengerId={passenger_id}")
    assert response.status_code == 200
    tickets = response.json()
    assert len(tickets) == 1
    assert tickets[0]["passengerId"] == passenger_id
    
    # Проверка фильтра по статусу
    response = requests.get(f"{base_url}/v1/tickets?status=active")
    assert response.status_code == 200
    print("✅ GET /tickets with filters works")

def test_get_ticket_by_id(base_url, setup_test_flight):
    """C1: GET /v1/tickets/{ticketId}"""
    flight = setup_test_flight
    
    # Создаем билет
    passenger_id = str(uuid.uuid4())
    buy_response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": passenger_id,
            "passengerName": "Тест",
            "flightId": flight["flightId"]
        }
    )
    created_ticket = buy_response.json()
    ticket_id = created_ticket["ticketId"]
    
    # Получаем билет по ID
    response = requests.get(f"{base_url}/v1/tickets/{ticket_id}")
    assert response.status_code == 200
    ticket = response.json()
    assert ticket["ticketId"] == ticket_id
    assert ticket["passengerId"] == passenger_id
    print("✅ GET /tickets/{ticketId} works")

def test_get_passenger_tickets(base_url, setup_test_flight):
    """C1: GET /v1/tickets/passenger/{passengerId}"""
    flight = setup_test_flight
    passenger_id = str(uuid.uuid4())
    
    # Создаем билет для пассажира
    requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": passenger_id,
            "passengerName": "Тест",
            "flightId": flight["flightId"]
        }
    )
    
    # Получаем билеты пассажира
    response = requests.get(f"{base_url}/v1/tickets/passenger/{passenger_id}")
    assert response.status_code == 200
    tickets = response.json()
    assert len(tickets) == 1
    assert tickets[0]["passengerId"] == passenger_id
    print("✅ GET /tickets/passenger works")

def test_refund_ticket(base_url, setup_test_flight):
    """F5: POST /v1/tickets/{ticketId}/refund - возврат билета"""
    flight = setup_test_flight
    
    # Создаем билет
    buy_response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": str(uuid.uuid4()),
            "passengerName": "Иван Петров",
            "flightId": flight["flightId"]
        }
    )
    ticket = buy_response.json()
    ticket_id = ticket["ticketId"]
    
    # Проверяем статистику до возврата
    sales_before = requests.get(f"{base_url}/v1/flight-sales/{flight['flightId']}").json()
    assert sales_before["activeTotal"] == 1
    
    # Возвращаем билет
    refund_response = requests.post(
        f"{base_url}/v1/tickets/{ticket_id}/refund",
        json={"reason": "client_request"}
    )
    assert refund_response.status_code == 200
    refunded = refund_response.json()
    assert refunded["status"] == "returned"
    
    # Проверяем статистику после возврата
    sales_after = requests.get(f"{base_url}/v1/flight-sales/{flight['flightId']}").json()
    assert sales_after["soldTotal"] == 1  # Не меняется
    assert sales_after["activeTotal"] == 0  # Уменьшилось
    
    print("✅ Manual refund works")