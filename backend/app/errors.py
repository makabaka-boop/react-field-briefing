"""统一 API 错误类型与错误响应格式。"""


class ApiError(Exception):
    """业务错误，携带 HTTP 状态码、错误码、消息与可选明细。"""

    def __init__(self, status, error_code, message, details=None):
        super().__init__(message)
        self.status = status
        self.error_code = error_code
        self.message = message
        self.details = details if details is not None else {}

    def to_body(self):
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


def bad_request(message, details=None, error_code="VALIDATION_ERROR"):
    return ApiError(400, error_code, message, details)


def not_found(message, details=None, error_code="NOT_FOUND"):
    return ApiError(404, error_code, message, details)


def conflict(message, details=None, error_code="CONFLICT"):
    return ApiError(409, error_code, message, details)
