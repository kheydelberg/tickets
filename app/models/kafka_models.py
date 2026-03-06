from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Any, Dict
import uuid

class KafkaEnvelope(BaseModel):
    """
    Единый формат для всех Kafka сообщений (из документации)
    {
        "eventId": "uuid",
        "type": "string",
        "ts": "ISO-8601",
        "producer": "string",
        "correlationId": "uuid|null",
        "entity": {"kind": "string", "id": "string"},
        "payload": {}
    }
    """
    eventId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    ts: datetime = Field(default_factory=datetime.utcnow)
    producer: str = "tickets"
    correlationId: Optional[str] = None
    entity: Dict[str, str]
    payload: Dict[str, Any]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Модели для входящих событий
class FlightCreatedPayload(BaseModel):
    flightId: str
    plannedCapacity: int
    scheduledDeparture: datetime

class FlightStatusChangedPayload(BaseModel):
    flightId: str
    oldStatus: str
    newStatus: str

class PassengerCreatedPayload(BaseModel):
    passengerId: str
    passengerName: str
    flightId: str
    isVIP: bool = False
    menuType: Optional[str] = None
    baggageWeight: int = 0

class BoardingResultPayload(BaseModel):
    flightId: str
    boardedPassengerIds: list[str]
    bumpedPassengerIds: list[str]