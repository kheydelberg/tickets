from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.main import app
import logging

logger = logging.getLogger(__name__)

# Формат ошибок из документации
def error_response(code: str, message: str) -> dict:
    return {"code": code, "message": message}

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """400 Validation Error"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_response("validation_error", str(exc))
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """409 Conflict для бизнес-ошибок"""
    error_messages = {
        "Sales not initialized": "sales_not_initialized",
        "Sales are closed": "sales_closed",
        "Sales limit reached": "sold_out",
        "already has active ticket": "already_has_active_ticket",
        "Refund is not allowed": "refund_closed",
        "Ticket not found": "not_found",
    }
    
    error_str = str(exc)
    code = "conflict"
    
    for msg, err_code in error_messages.items():
        if msg in error_str:
            code = err_code
            break
    
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=error_response(code, error_str)
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """500 Internal Error"""
    logger.error(f"Internal error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response("internal_error", "Internal server error")
    )