from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    error_code: str = "internal_error"
    status_code: int = 500

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppError):
    error_code = "not_found"
    status_code = 404


class ValidationError(AppError):
    error_code = "validation_error"
    status_code = 422


class ConflictError(AppError):
    error_code = "conflict"
    status_code = 409


class InvalidStatusTransitionError(AppError):
    error_code = "invalid_status_transition"
    status_code = 400


class BadRequestError(AppError):
    error_code = "bad_request"
    status_code = 400


def error_response(error_code: str, message: str, details: dict, status_code: int):
    return JSONResponse(
        status_code=status_code,
        content={
            "error_code": error_code,
            "message": message,
            "details": details,
        },
    )


def register_error_handlers(app):
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError):
        return error_response(exc.error_code, exc.message, exc.details, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError):
        fields: list[str] = []
        for err in exc.errors():
            loc = ".".join(str(p) for p in err.get("loc", []) if p != "body")
            fields.append(loc or err.get("type", "invalid"))
        return error_response(
            "validation_error",
            "Request validation failed. Check required fields and allowed values.",
            {"fields": fields, "errors": exc.errors()},
            422,
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception):
        return error_response(
            "internal_error",
            "An unexpected error occurred.",
            {"exception": str(exc)},
            500,
        )
