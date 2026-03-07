import json
import uuid
from datetime import datetime

def test_envelope_format():
    """C2: Проверка формата Kafka Envelope"""
    from app.models.kafka_models import KafkaEnvelope
    
    # Создаем тестовый envelope
    envelope = KafkaEnvelope(
        type="test.event",
        producer="tickets",
        entity={"kind": "test", "id": str(uuid.uuid4())},
        payload={"test": "data"}
    )
    
    # Конвертируем в dict для проверки
    data = envelope.dict()
    
    # Проверяем все обязательные поля
    assert "eventId" in data
    assert "type" in data
    assert "ts" in data
    assert "producer" in data
    assert "entity" in data
    assert "payload" in data
    assert "correlationId" in data
    
    # Проверяем форматы
    assert data["producer"] == "tickets"
    assert data["type"] == "test.event"
    assert isinstance(data["entity"], dict)
    assert "kind" in data["entity"]
    assert "id" in data["entity"]
    
    print("✅ Kafka Envelope format matches specification")

def test_envelope_serialization():
    """Проверка сериализации datetime в JSON"""
    from app.utils.json_encoder import CustomJSONEncoder
    from app.models.kafka_models import KafkaEnvelope
    import json
    
    envelope = KafkaEnvelope(
        type="test.event",
        producer="tickets",
        entity={"kind": "test", "id": "test-id"},
        payload={"timestamp": datetime.now()}
    )
    
    # Сериализуем с кастомным encoder
    json_str = json.dumps(envelope.dict(), cls=CustomJSONEncoder)
    data = json.loads(json_str)
    
    # Проверяем что дата конвертировалась в строку
    assert isinstance(data["payload"]["timestamp"], str)
    print("✅ Envelope serialization works with datetime")