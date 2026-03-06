from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.flight_sales import FlightSales

router = APIRouter(prefix="/v1/flight-sales", tags=["Sales"])

@router.get("/{flight_id}")
async def get_flight_sales(
    flight_id: str,
    db: Session = Depends(get_db)
):
    """GET /v1/flight-sales/{flightId} - состояние продаж по рейсу"""
    flight_sales = db.query(FlightSales).filter(
        FlightSales.flight_id == flight_id
    ).first()
    
    if not flight_sales:
        raise HTTPException(status_code=404, detail="Flight sales not found")
    
    return flight_sales.to_dict()