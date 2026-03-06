from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.services.ticket_service import TicketService
from app.models.ticket import Ticket, TicketStatusEnum
from app.utils.idempotency import IdempotencyUtils
import logging

router = APIRouter(prefix="/v1/tickets", tags=["Tickets"])
logger = logging.getLogger(__name__)

# Pydantic модели для запросов/ответов
from pydantic import BaseModel

class BuyTicketRequest(BaseModel):
    passengerId: str
    passengerName: str
    flightId: str
    isVIP: bool = False
    menuType: Optional[str] = None
    baggageWeight: int = 0

class RefundTicketRequest(BaseModel):
    reason: str

class TicketResponse(BaseModel):
    ticketId: str
    passengerId: str
    passengerName: str
    flightId: str
    status: str
    isVIP: bool
    menuType: Optional[str]
    baggageWeight: int
    createdAt: Optional[str]
    updatedAt: Optional[str]

@router.get("/health")
async def health_check():
    """GET /health"""
    return {"status": "ok"}

@router.get("", response_model=List[TicketResponse])
async def list_tickets(
    flightId: Optional[str] = Query(None, description="Filter by flight ID"),
    passengerId: Optional[str] = Query(None, description="Filter by passenger ID"),
    status: Optional[TicketStatusEnum] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """GET /v1/tickets - список билетов с фильтрацией"""
    query = db.query(Ticket)
    
    if flightId:
        query = query.filter(Ticket.flight_id == flightId)
    if passengerId:
        query = query.filter(Ticket.passenger_id == passengerId)
    if status:
        query = query.filter(Ticket.status == status)
    
    tickets = query.all()
    return [t.to_dict() for t in tickets]

@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    db: Session = Depends(get_db)
):
    """GET /v1/tickets/{ticketId}"""
    try:
        ticket = db.query(Ticket).filter(
            Ticket.ticket_id == ticket_id
        ).first()
        
        if not ticket:
            raise ValueError("Ticket not found")
        
        return ticket.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/passenger/{passenger_id}", response_model=List[TicketResponse])
async def get_passenger_tickets(
    passenger_id: str,
    db: Session = Depends(get_db)
):
    """GET /v1/tickets/passenger/{passengerId}"""
    tickets = db.query(Ticket).filter(
        Ticket.passenger_id == passenger_id
    ).all()
    
    return [t.to_dict() for t in tickets]

@router.post("/buy", response_model=TicketResponse, status_code=201)
async def buy_ticket_manual(
    request: BuyTicketRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db)
):
    """F4: POST /v1/tickets/buy - ручная покупка билета"""
    try:
        # Проверка идемпотентности для REST
        if idempotency_key:
            if IdempotencyUtils.is_event_processed(db, idempotency_key):
                # В реальном проекте тут нужно вернуть ранее созданный билет
                pass
        
        ticket = TicketService.buy_ticket(
            db=db,
            passenger_id=request.passengerId,
            passenger_name=request.passengerName,
            flight_id=request.flightId,
            is_vip=request.isVIP,
            menu_type=request.menuType,
            baggage_weight=request.baggageWeight
        )
        
        if not ticket:
            raise ValueError("Could not buy ticket: sales closed or limit reached")
        
        # Сохраняем idempotency mapping
        if idempotency_key:
            # В реальном проекте тут нужно сохранить связь ключ->билет
            pass
        
        return ticket
        
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.post("/{ticket_id}/refund", response_model=TicketResponse)
async def refund_ticket_manual(
    ticket_id: str,
    request: RefundTicketRequest,
    db: Session = Depends(get_db)
):
    """F5: POST /v1/tickets/{ticketId}/refund - ручной возврат"""
    try:
        ticket = TicketService.refund_ticket(
            db=db,
            ticket_id=ticket_id,
            reason=request.reason
        )
        return ticket
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))