from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, error_code: str, message: str, details: dict = None, status_code: int = 400):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.status_code = status_code


class NotFoundError(AppError):
    def __init__(self, entity: str, entity_id=None):
        details = {"entity": entity}
        if entity_id is not None:
            details["id"] = entity_id
        super().__init__(
            error_code="not_found",
            message=f"{entity} not found",
            details=details,
            status_code=404,
        )


class ValidationError(AppError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            error_code="validation_error",
            message=message,
            details=details or {},
            status_code=422,
        )


class ConflictError(AppError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            error_code="conflict",
            message=message,
            details=details or {},
            status_code=409,
        )


class StateTransitionError(AppError):
    def __init__(self, current_status: str, target_status: str, allowed: list):
        super().__init__(
            error_code="invalid_state_transition",
            message=f"Cannot transition from {current_status} to {target_status}",
            details={
                "current_status": current_status,
                "target_status": target_status,
                "allowed_transitions": allowed,
            },
            status_code=409,
        )


async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )
