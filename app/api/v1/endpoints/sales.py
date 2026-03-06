from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.models.flight_sales import FlightSales

router = APIRouter(tags=["Sales"])  # Убрали prefix

@router.get("/v1/flight-sales")  # GET /v1/flight-sales
async def list_flight_sales(
    db: Session = Depends(get_db)
):
    """GET /v1/flight-sales - список всех рейсов с продажами"""
    flight_sales = db.query(FlightSales).all()
    return [fs.to_dict() for fs in flight_sales]

@router.get("/v1/flight-sales/{flight_id}")  # GET /v1/flight-sales/{flightId}
async def get_flight_sales(
    flight_id: str,
    db: Session = Depends(get_db)
):
    flight_sales = db.query(FlightSales).filter(
        FlightSales.flight_id == flight_id
    ).first()
    
    if not flight_sales:
        raise HTTPException(status_code=404, detail="Flight sales not found")
    
    return flight_sales.to_dict()