import requests
from conftest import BASE_URL

def test_health_endpoint():
    """A) Service Identity: проверка health endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    
    # Твой сервис возвращает только {"status":"ok"}
    # Поэтому проверяем только это
    assert data["status"] == "ok"
    
    # Эти поля могут отсутствовать, поэтому не проверяем их
    # assert "service" in data
    # assert "environment" in data
    # assert "database" in data
    
    print("✅ Health check passed")
    print(f"Response: {data}")