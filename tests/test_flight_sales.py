import requests
import uuid
from conftest import BASE_URL

def test_get_flight_sales_existing(base_url, setup_test_flight):
    """GET /v1/flight-sales/{flightId} - существующий рейс"""
    flight = setup_test_flight
    response = requests.get(f"{base_url}/v1/flight-sales/{flight['flightId']}")
    assert response.status_code == 200
    data = response.json()
    assert data["flightId"] == flight["flightId"]
    assert data["plannedCapacity"] == flight["plannedCapacity"]
    assert data["overbookLimit"] == flight["overbookLimit"]
    assert "soldTotal" in data
    assert "activeTotal" in data
    assert "salesOpen" in data
    print("✅ GET flight-sales works")

def test_get_flight_sales_not_found(base_url):
    """GET /v1/flight-sales/{flightId} - несуществующий рейс"""
    fake_id = f"FAKE{str(uuid.uuid4())[:8]}"
    response = requests.get(f"{base_url}/v1/flight-sales/{fake_id}")
    assert response.status_code == 404
    print("✅ GET flight-sales not found returns 404")

def test_flight_sales_initial_state(base_url, setup_test_flight):
    """Проверка начального состояния flight_sales"""
    flight = setup_test_flight
    response = requests.get(f"{base_url}/v1/flight-sales/{flight['flightId']}")
    data = response.json()
    assert data["soldTotal"] == 0
    assert data["activeTotal"] == 0
    assert data["salesOpen"] == True
    print("✅ Flight sales initial state correct")

def test_flight_sales_after_buy(base_url, setup_test_flight):
    """Проверка обновления flight_sales после покупки"""
    flight = setup_test_flight
    
    # Покупаем билет
    requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": str(uuid.uuid4()),
            "passengerName": "Test",
            "flightId": flight["flightId"]
        }
    )
    
    # Проверяем счетчики
    response = requests.get(f"{base_url}/v1/flight-sales/{flight['flightId']}")
    data = response.json()
    assert data["soldTotal"] == 1
    assert data["activeTotal"] == 1
    print("✅ Flight sales updated after buy")

def test_flight_sales_after_refund(base_url, setup_test_flight):
    """Проверка обновления flight_sales после возврата"""
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
    
    # Возвращаем
    requests.post(
        f"{base_url}/v1/tickets/{ticket['ticketId']}/refund",
        json={"reason": "test"}
    )
    
    # Проверяем счетчики
    response = requests.get(f"{base_url}/v1/flight-sales/{flight['flightId']}")
    data = response.json()
    assert data["soldTotal"] == 1  # не меняется
    assert data["activeTotal"] == 0  # уменьшается
    print("✅ Flight sales updated after refund")

def test_flight_sales_overbook_limit(base_url, setup_test_flight):
    """Проверка правильности расчета overbook_limit"""
    flight = setup_test_flight
    response = requests.get(f"{base_url}/v1/flight-sales/{flight['flightId']}")
    data = response.json()
    expected_limit = int(flight["plannedCapacity"] * 0.3)  # overbook_factor = 0.3
    assert data["overbookLimit"] == expected_limit
    print(f"✅ Overbook limit correct: {data['overbookLimit']}")