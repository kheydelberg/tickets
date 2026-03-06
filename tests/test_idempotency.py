# tests/test_idempotency.py
import requests
import uuid
from conftest import BASE_URL

def test_idempotency_buy_ticket(base_url, setup_test_flight):
    """Проверка идемпотентности покупки с Idempotency-Key"""
    flight = setup_test_flight
    idempotency_key = str(uuid.uuid4())
    
    # Первый запрос
    response1 = requests.post(
        f"{base_url}/v1/tickets/buy",
        headers={"Idempotency-Key": idempotency_key},
        json={
            "passengerId": str(uuid.uuid4()),
            "passengerName": "Тест",
            "flightId": flight["flightId"]
        }
    )
    assert response1.status_code == 201
    ticket1 = response1.json()
    
    # Второй запрос с тем же ключом
    response2 = requests.post(
        f"{base_url}/v1/tickets/buy",
        headers={"Idempotency-Key": idempotency_key},
        json={
            "passengerId": str(uuid.uuid4()),
            "passengerName": "Тест",
            "flightId": flight["flightId"]
        }
    )
    
    # Должен вернуть тот же билет или ошибку
    if response2.status_code == 201:
        ticket2 = response2.json()
        assert ticket2["ticketId"] == ticket1["ticketId"]
    else:
        assert response2.status_code == 409
    
    print("✅ Idempotency-Key works")