from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.models.flight_sales import FlightSales
from fastapi.responses import JSONResponse
import logging

router = APIRouter(tags=["Sales"])  # Убрали prefix
logger = logging.getLogger(__name__)

@router.get("/v1/flight-sales")  # GET /v1/flight-sales
async def list_flight_sales(
    db: Session = Depends(get_db)
):
    """GET /v1/flight-sales - список всех рейсов с продажами"""
    flight_sales = db.query(FlightSales).all()
    return [fs.to_dict() for fs in flight_sales]

@router.get("/v1/flight-sales/{flight_id}")
async def get_flight_sales(flight_id: str, db: Session = Depends(get_db)):
    try:
        flight_sales = db.query(FlightSales).filter(FlightSales.flight_id == flight_id).first()
        if not flight_sales:
            return JSONResponse(
                status_code=404,
                content={"code": "not_found", "message": f"Flight sales not found for {flight_id}"}
            )
        return flight_sales.to_dict()
    except Exception as e:
        logger.error(f"Error getting flight sales: {e}")
        return JSONResponse(
            status_code=500,
            content={"code": "internal_error", "message": "Internal server error"}
        )