from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging

logger = logging.getLogger(__name__)

# Функция для создания ответа с ошибкой в формате документации
def error_response(code: str, message: str) -> dict:
    """Формат ошибки согласно спецификации OpenAPI"""
    return {"code": code, "message": message}

# Обработчик для 400 Validation Error
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """400 Validation Error - ошибки валидации входных данных"""
    errors = exc.errors()
    if errors and len(errors) > 0:
        field = errors[0].get('loc', ['unknown'])[-1]
        msg = errors[0].get('msg', 'Validation error')
        message = f"{field}: {msg}"
    else:
        message = "Validation error"
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_response("validation_error", message)
    )

# Обработчик для 404 Not Found
async def not_found_handler(request: Request, exc: Exception):
    """404 Not Found"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=error_response("not_found", str(exc) if str(exc) else "Resource not found")
    )

# Обработчик для 409 Conflict (бизнес-ошибки)
async def conflict_handler(request: Request, exc: Exception):
    """409 Conflict для бизнес-ошибок с разными кодами"""
    error_str = str(exc)
    
    # Маппинг сообщений на коды ошибок из спецификации
    error_mapping = {
        "Sales not initialized": "sales_not_initialized",
        "Sales are closed": "sales_closed",
        "Sales limit reached": "sold_out",
        "already has active ticket": "already_has_active_ticket",
        "Refund is not allowed": "refund_closed",
        "Ticket not found": "not_found",
    }
    
    # По умолчанию - conflict
    code = "conflict"
    
    # Ищем соответствие
    for msg, err_code in error_mapping.items():
        if msg in error_str:
            code = err_code
            break
    
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=error_response(code, error_str)
    )

# Обработчик для 500 Internal Error
async def internal_error_handler(request: Request, exc: Exception):
    """500 Internal Error"""
    logger.error(f"Internal error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response("internal_error", "Internal server error")
    )