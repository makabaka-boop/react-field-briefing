"""Application-wide error types.

All API error responses are serialized to the fixed shape:
    {"error_code": "...", "message": "...", "details": {...}}
"""


class ApiError(Exception):
    """Base class for errors that map to a structured API response."""

    status_code = 400
    error_code = "bad_request"

    def __init__(self, message, details=None, error_code=None, status_code=None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        if error_code is not None:
            self.error_code = error_code
        if status_code is not None:
            self.status_code = status_code

    def to_dict(self):
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class ValidationError(ApiError):
    status_code = 422
    error_code = "validation_error"


class NotFoundError(ApiError):
    status_code = 404
    error_code = "not_found"


class ConflictError(ApiError):
    status_code = 409
    error_code = "conflict"


class InvalidTransitionError(ApiError):
    status_code = 409
    error_code = "invalid_transition"


class MethodNotAllowedError(ApiError):
    status_code = 405
    error_code = "method_not_allowed"
