from fastapi import APIRouter, Depends, Header, Query, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.services.ticket_service import TicketService
from app.models.ticket import Ticket, TicketStatusEnum
from app.utils.idempotency import IdempotencyUtils
from app.api.v1.errors import error_response
import logging
from pydantic import BaseModel

router = APIRouter(tags=["Tickets"])
logger = logging.getLogger(__name__)

# Pydantic модели
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
    
    class Config:
        from_attributes = True

@router.get("/health")
async def health_check():
    return {"status": "ok"}

@router.get("/v1/tickets", response_model=List[TicketResponse])
async def list_tickets(
    flightId: Optional[str] = Query(None),
    passengerId: Optional[str] = Query(None),
    status: Optional[TicketStatusEnum] = Query(None),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(Ticket)
        if flightId:
            query = query.filter(Ticket.flight_id == flightId)
        if passengerId:
            query = query.filter(Ticket.passenger_id == passengerId)
        if status:
            query = query.filter(Ticket.status == status)
        return [t.to_dict() for t in query.all()]
    except Exception as e:
        logger.error(f"Error listing tickets: {e}")
        raise HTTPException(
            status_code=500,
            detail=error_response("internal_error", "Internal server error")
        )

@router.get("/v1/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str, db: Session = Depends(get_db)):
    try:
        ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
        if not ticket:
            raise HTTPException(
                status_code=404,
                detail=error_response("not_found", "Ticket not found")
            )
        return ticket.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ticket: {e}")
        raise HTTPException(
            status_code=500,
            detail=error_response("internal_error", "Internal server error")
        )

@router.get("/v1/tickets/passenger/{passenger_id}", response_model=List[TicketResponse])
async def get_passenger_tickets(passenger_id: str, db: Session = Depends(get_db)):
    try:
        tickets = db.query(Ticket).filter(Ticket.passenger_id == passenger_id).all()
        return [t.to_dict() for t in tickets]
    except Exception as e:
        logger.error(f"Error getting passenger tickets: {e}")
        raise HTTPException(
            status_code=500,
            detail=error_response("internal_error", "Internal server error")
        )

@router.post("/v1/tickets/buy", response_model=TicketResponse, status_code=201)
async def buy_ticket_manual(
    request: BuyTicketRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db)
):
    try:
        ticket = TicketService.buy_ticket(
            db=db,
            passenger_id=request.passengerId,
            passenger_name=request.passengerName,
            flight_id=request.flightId,
            is_vip=request.isVIP,
            menu_type=request.menuType,
            baggage_weight=request.baggageWeight,
            idempotency_key=idempotency_key
        )
        
        return ticket
        
    except ValueError as e:
        error_msg = str(e)
        logger.warning(f"Business error buying ticket: {error_msg}")
        
        # Определяем код ошибки из сообщения
        error_code = "conflict"
        if "Sales not initialized" in error_msg:
            error_code = "sales_not_initialized"
        elif "Sales are closed" in error_msg:
            error_code = "sales_closed"
        elif "Sales limit reached" in error_msg:
            error_code = "sold_out"
        elif "already has active ticket" in error_msg:
            error_code = "already_has_active_ticket"
        
        return JSONResponse(
            status_code=409,
            content={"code": error_code, "message": error_msg}
        )
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"code": "internal_error", "message": "Internal server error"}
        )

@router.post("/v1/tickets/{ticket_id}/refund", response_model=TicketResponse)
async def refund_ticket_manual(
    ticket_id: str,
    request: RefundTicketRequest,
    db: Session = Depends(get_db)
):
    try:
        ticket = TicketService.refund_ticket(
            db=db,
            ticket_id=ticket_id,
            reason=request.reason
        )
        return ticket
        
    except ValueError as e:
        error_msg = str(e)
        logger.warning(f"Business error refunding ticket: {error_msg}")
        
        if "Ticket not found" in error_msg:
            return JSONResponse(
                status_code=404,
                content={"code": "not_found", "message": error_msg}
            )
        elif "Refund is not allowed after sales closed" in error_msg:
            return JSONResponse(
                status_code=409,
                content={"code": "refund_closed", "message": error_msg}
            )
        elif "Only active tickets can be refunded" in error_msg:
            return JSONResponse(
                status_code=409,
                content={"code": "invalid_status", "message": error_msg}
            )
        else:
            return JSONResponse(
                status_code=409,
                content={"code": "conflict", "message": error_msg}
            )
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"code": "internal_error", "message": "Internal server error"}
        )

@router.get("/v1/tickets/{ticket_id}/history", response_model=List[TicketResponse])
async def get_ticket_history(ticket_id: str, db: Session = Depends(get_db)):
    try:
        ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
        if not ticket:
            raise HTTPException(
                status_code=404,
                detail=error_response("not_found", "Ticket not found")
            )
        return [ticket.to_dict()]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ticket history: {e}")
        raise HTTPException(
            status_code=500,
            detail=error_response("internal_error", "Internal server error")
        )