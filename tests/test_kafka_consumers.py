import pytest
import json
import uuid
import time
from conftest import BASE_URL, KAFKA_AVAILABLE
import requests


pytestmark = pytest.mark.skipif(not KAFKA_AVAILABLE, reason="Kafka not available")

def test_consume_flight_created(kafka_producer, test_flight, base_url):
    """F1: Проверка создания flight_sales по событию flight.created"""
    flight_id = f"KAFKA{str(uuid.uuid4())[:8]}"
    
    # Отправляем событие flight.created
    event = {
        "eventId": str(uuid.uuid4()),
        "type": "flight.created",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "producer": "flights",
        "entity": {"kind": "flight", "id": flight_id},
        "payload": {
            "flightId": flight_id,
            "plannedCapacity": 200,
            "scheduledDeparture": "2026-03-07T10:00:00Z"
        }
    }
    
    future = kafka_producer.send('flights.events', value=event)
    future.get(timeout=10)
    
    # Ждем обработки
    time.sleep(2)
    
    # Проверяем создание flight_sales
    response = requests.get(f"{base_url}/v1/flight-sales/{flight_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["flightId"] == flight_id
    assert data["plannedCapacity"] == 200
    assert data["overbookLimit"] == 60  # 200 * 0.3
    assert data["salesOpen"] == True
    print("✅ F1: flight.created consumed and flight_sales created")

def test_consume_flight_status_changed(kafka_producer, setup_test_flight, base_url):
    """F2: Проверка закрытия продаж по flight.status.changed"""
    flight = setup_test_flight
    
    # Отправляем событие статуса RegistrationOpen
    event = {
        "eventId": str(uuid.uuid4()),
        "type": "flight.status.changed",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "producer": "flights",
        "entity": {"kind": "flight", "id": flight["flightId"]},
        "payload": {
            "flightId": flight["flightId"],
            "oldStatus": "Scheduled",
            "newStatus": "RegistrationOpen"
        }
    }
    
    future = kafka_producer.send('flights.events', value=event)
    future.get(timeout=10)
    
    # Ждем обработки
    time.sleep(2)
    
    # Проверяем что продажи закрыты
    response = requests.get(f"{base_url}/v1/flight-sales/{flight['flightId']}")
    assert response.status_code == 200
    data = response.json()
    assert data["salesOpen"] == False
    print("✅ F2: flight.status.changed consumed and sales closed")

def test_consume_passenger_created(kafka_producer, setup_test_flight, base_url):
    """F3: Проверка авто-покупки билета по passenger.created"""
    flight = setup_test_flight
    passenger_id = str(uuid.uuid4())
    
    # Отправляем событие создания пассажира
    event = {
        "eventId": str(uuid.uuid4()),
        "type": "passenger.created",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "producer": "passengers",
        "entity": {"kind": "passenger", "id": passenger_id},
        "payload": {
            "passengerId": passenger_id,
            "passengerName": "Auto Passenger",
            "flightId": flight["flightId"],
            "isVIP": True,
            "menuType": "chicken",
            "baggageWeight": 20
        }
    }
    
    future = kafka_producer.send('passengers.events', value=event)
    future.get(timeout=10)
    
    # Ждем обработки
    time.sleep(2)
    
    # Проверяем создание билета
    response = requests.get(f"{base_url}/v1/tickets?passengerId={passenger_id}")
    assert response.status_code == 200
    tickets = response.json()
    assert len(tickets) == 1
    assert tickets[0]["status"] == "active"
    assert tickets[0]["passengerName"] == "Auto Passenger"
    
    # Проверяем счетчики
    sales = requests.get(f"{base_url}/v1/flight-sales/{flight['flightId']}").json()
    assert sales["soldTotal"] >= 1
    assert sales["activeTotal"] >= 1
    print("✅ F3: passenger.created consumed and ticket auto-bought")

def test_consume_boarding_result_bumped(kafka_producer, setup_test_flight, base_url):
    """F6: Проверка обработки овербукинга по board.boarding.result"""
    flight = setup_test_flight
    passenger_id = str(uuid.uuid4())
    
    # Сначала покупаем билет через API
    buy_response = requests.post(
        f"{base_url}/v1/tickets/buy",
        json={
            "passengerId": passenger_id,
            "passengerName": "Bumped Passenger",
            "flightId": flight["flightId"]
        }
    )
    assert buy_response.status_code == 201
    ticket = buy_response.json()
    
    # Отправляем событие посадки с bumped пассажиром
    event = {
        "eventId": str(uuid.uuid4()),
        "type": "board.boarding.result",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "producer": "boarding",
        "entity": {"kind": "flight", "id": flight["flightId"]},
        "payload": {
            "flightId": flight["flightId"],
            "boardedPassengerIds": [],
            "bumpedPassengerIds": [passenger_id]
        }
    }
    
    future = kafka_producer.send('board.events', value=event)
    future.get(timeout=10)
    
    # Ждем обработки
    time.sleep(2)
    
    # Проверяем что статус билета стал bumped
    response = requests.get(f"{base_url}/v1/tickets/{ticket['ticketId']}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "bumped"
    
    # Проверяем счетчики
    sales = requests.get(f"{base_url}/v1/flight-sales/{flight['flightId']}").json()
    assert sales["activeTotal"] == 0  # bumped пассажир не считается активным
    print("✅ F6: board.boarding.result consumed and ticket marked as bumped")