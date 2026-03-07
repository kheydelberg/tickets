from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.ticket import Ticket, TicketStatusEnum
from app.models.flight_sales import FlightSales
from app.models.outbox import OutboxMessage
from app.models.idempotency import IdempotencyKey  # Добавь эту модель
from app.models.kafka_models import KafkaEnvelope
from app.config import settings
from app.utils.json_encoder import CustomJSONEncoder
import logging
import uuid
import json
from datetime import datetime
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class TicketService:
    """Бизнес-логика работы с билетами"""
    
    @staticmethod
    def buy_ticket(
        db: Session, 
        passenger_id: str,
        passenger_name: str,
        flight_id: str,
        is_vip: bool = False,
        menu_type: Optional[str] = None,
        baggage_weight: int = 0,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        F3/F4: Покупка билета (авто или manual) с поддержкой идемпотентности
        """
        try:
            # Проверка идемпотентности - если ключ уже использован
            if idempotency_key:
                existing_key = db.query(IdempotencyKey).filter(
                    IdempotencyKey.key == idempotency_key
                ).first()
                
                if existing_key:
                    # Ключ уже использован - возвращаем существующий билет
                    logger.info(f"Idempotency key {idempotency_key} already used, returning existing ticket")
                    ticket_id = existing_key.response_data.get("ticketId")
                    if ticket_id:
                        ticket = db.query(Ticket).filter(
                            Ticket.ticket_id == uuid.UUID(ticket_id)
                        ).first()
                        if ticket:
                            return ticket.to_dict()
            
            # Блокируем запись о рейсе
            flight_sales = db.query(FlightSales).filter(
                FlightSales.flight_id == flight_id
            ).with_for_update().first()
            
            if not flight_sales:
                raise ValueError(f"Sales not initialized for flight {flight_id}")
            
            # F3: проверяем открыты ли продажи
            if not flight_sales.sales_open:
                logger.info(f"Sales closed for flight {flight_id}, cannot buy ticket")
                raise ValueError("Sales are closed for this flight")
            
            # F3: проверяем лимит продаж
            if flight_sales.active_total >= flight_sales.total_limit:
                logger.info(f"Sales limit reached for flight {flight_id}")
                raise ValueError("Sales limit reached (including overbooking limit)")
            
            # Проверяем, нет ли уже активного билета
            existing = db.query(Ticket).filter(
                Ticket.passenger_id == uuid.UUID(passenger_id),
                Ticket.flight_id == flight_id,
                Ticket.status == TicketStatusEnum.ACTIVE
            ).first()
            
            if existing:
                raise ValueError("Passenger already has active ticket for this flight")
            
            # Создаем билет с ВСЕМИ полями
            new_ticket = Ticket(
                ticket_id=uuid.uuid4(),
                passenger_id=uuid.UUID(passenger_id),
                passenger_name=passenger_name,
                flight_id=flight_id,
                status=TicketStatusEnum.ACTIVE,
                is_vip=is_vip,  # Обязательное поле
                menu_type=menu_type,
                baggage_weight=baggage_weight,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(new_ticket)
            
            # Обновляем счетчики
            flight_sales.sold_total += 1
            flight_sales.active_total += 1
            
            # Сохраняем ключ идемпотентности если есть
            if idempotency_key:
                idempotency_record = IdempotencyKey(
                    key=idempotency_key,
                    response_data={"ticketId": str(new_ticket.ticket_id)},
                    created_at=datetime.utcnow()
                )
                db.add(idempotency_record)
            
            # Создаем outbox сообщение
            envelope_data = {
                "eventId": str(uuid.uuid4()),
                "type": "ticket.bought",
                "ts": datetime.utcnow().isoformat(),
                "producer": "tickets",
                "correlationId": None,
                "entity": {"kind": "ticket", "id": str(new_ticket.ticket_id)},
                "payload": {
                    "ticketId": str(new_ticket.ticket_id),
                    "passengerId": passenger_id,
                    "passengerName": passenger_name,
                    "flightId": flight_id,
                    "status": "active",
                    "isVIP": is_vip,
                    "menuType": menu_type,
                    "baggageWeight": baggage_weight
                }
            }
            
            outbox = OutboxMessage(
                topic=settings.kafka_topic_tickets_events,
                key=str(new_ticket.ticket_id),
                value=envelope_data
            )
            db.add(outbox)
            
            db.commit()
            db.refresh(new_ticket)
            
            logger.info(f"Ticket {new_ticket.ticket_id} bought for flight {flight_id}")
            return new_ticket.to_dict()
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error buying ticket: {e}")
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error buying ticket: {e}")
            raise
    
    @staticmethod
    def refund_ticket(
        db: Session,
        ticket_id: str,
        reason: str,
        idempotency_key: Optional[str] = None  # Добавлен параметр
    ) -> Dict[str, Any]:
        """
        F5: Возврат билета с поддержкой идемпотентности
        """
        try:
            # Проверка идемпотентности для возврата
            if idempotency_key:
                existing_key = db.query(IdempotencyKey).filter(
                    IdempotencyKey.key == idempotency_key
                ).first()
                
                if existing_key:
                    logger.info(f"Idempotency key {idempotency_key} already used for refund")
                    ticket_id_from_key = existing_key.response_data.get("ticketId")
                    if ticket_id_from_key:
                        ticket = db.query(Ticket).filter(
                            Ticket.ticket_id == uuid.UUID(ticket_id_from_key)
                        ).first()
                        if ticket:
                            return ticket.to_dict()
            
            # Блокируем билет
            ticket = db.query(Ticket).filter(
                Ticket.ticket_id == uuid.UUID(ticket_id)
            ).with_for_update().first()
            
            if not ticket:
                raise ValueError("Ticket not found")
            
            if ticket.status != TicketStatusEnum.ACTIVE:
                raise ValueError("Only active tickets can be refunded")
            
            # Блокируем запись о рейсе
            flight_sales = db.query(FlightSales).filter(
                FlightSales.flight_id == ticket.flight_id
            ).with_for_update().first()
            
            # F5: проверяем открыты ли продажи
            if not flight_sales or not flight_sales.sales_open:
                raise ValueError("Refund is not allowed after sales closed")
            
            # Обновляем статус билета
            old_status = ticket.status
            ticket.status = TicketStatusEnum.RETURNED
            
            # Обновляем счетчики
            flight_sales.active_total -= 1
            
            # Сохраняем ключ идемпотентности если есть
            if idempotency_key:
                idempotency_record = IdempotencyKey(
                    key=idempotency_key,
                    response_data={"ticketId": str(ticket.ticket_id)},
                    created_at=datetime.utcnow()
                )
                db.add(idempotency_record)
            
            # Создаем outbox сообщение для ticket.refunded
            envelope_data = {
                "eventId": str(uuid.uuid4()),
                "type": "ticket.refunded",
                "ts": datetime.utcnow().isoformat(),
                "producer": "tickets",
                "correlationId": None,
                "entity": {"kind": "ticket", "id": str(ticket.ticket_id)},
                "payload": {
                    "ticketId": str(ticket.ticket_id),
                    "passengerId": str(ticket.passenger_id),
                    "passengerName": ticket.passenger_name,
                    "flightId": ticket.flight_id,
                    "reason": reason,
                    "oldStatus": old_status.value
                }
            }
            
            outbox = OutboxMessage(
                topic=settings.kafka_topic_tickets_events,
                key=str(ticket.ticket_id),
                value=envelope_data
            )
            db.add(outbox)
            
            db.commit()
            db.refresh(ticket)
            
            logger.info(f"Ticket {ticket_id} refunded, reason: {reason}")
            return ticket.to_dict()
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error refunding ticket {ticket_id}: {e}")
            raise
    
    @staticmethod
    def process_boarding_result(
        db: Session,
        flight_id: str,
        bumped_passenger_ids: list[str]
    ) -> None:
        """
        F6: Обработка результатов посадки (overbooking)
        - для каждого bumpedPassengerId найти active ticket
        - поставить status=bumped
        - publish ticket.bumped
        """
        try:
            # Блокируем запись о рейсе
            flight_sales = db.query(FlightSales).filter(
                FlightSales.flight_id == flight_id
            ).with_for_update().first()
            
            if not flight_sales:
                logger.error(f"Flight sales not found for {flight_id}")
                return
            
            for passenger_id in bumped_passenger_ids:
                # Находим активный билет пассажира
                ticket = db.query(Ticket).filter(
                    Ticket.passenger_id == uuid.UUID(passenger_id),
                    Ticket.flight_id == flight_id,
                    Ticket.status == TicketStatusEnum.ACTIVE
                ).with_for_update().first()
                
                if ticket:
                    # Меняем статус на bumped
                    old_status = ticket.status
                    ticket.status = TicketStatusEnum.BUMPED
                    
                    # Обновляем счетчики
                    flight_sales.active_total -= 1
                    
                    # Создаем outbox сообщение для ticket.bumped
                    envelope_data = {
                        "eventId": str(uuid.uuid4()),
                        "type": "ticket.bumped",
                        "ts": datetime.utcnow().isoformat(),
                        "producer": "tickets",
                        "correlationId": None,
                        "entity": {"kind": "ticket", "id": str(ticket.ticket_id)},
                        "payload": {
                            "ticketId": str(ticket.ticket_id),
                            "passengerId": passenger_id,
                            "passengerName": ticket.passenger_name,
                            "flightId": flight_id,
                            "reason": "overbooking",
                            "oldStatus": old_status.value
                        }
                    }
                    
                    outbox = OutboxMessage(
                        topic=settings.kafka_topic_tickets_events,
                        key=str(ticket.ticket_id),
                        value=envelope_data
                    )
                    db.add(outbox)
                    
                    logger.info(f"Ticket {ticket.ticket_id} marked as bumped due to overbooking")
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error processing boarding result: {e}")
            raise