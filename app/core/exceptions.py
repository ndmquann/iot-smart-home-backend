class SmartHomeException(Exception):
    """Base exception class for the Smart Home API."""
    def __init__(self, message: str, error_code: int, status_code: int):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code

class NotFoundException(SmartHomeException):
    def __init__(self, detail: str):
        super().__init__(
            message=detail, 
            error_code="NOT_FOUND", 
            status_code=404
        )

class UnauthorizedException(SmartHomeException):
    def __init__(self, detail: str = "You are not authorized to perform this action."):
        super().__init__(
            message=detail, 
            error_code="UNAUTHORIZED", 
            status_code=403
        )

class BadRequestException(SmartHomeException):
    def __init__(self, detail: str):
        super().__init__(
            message=detail, 
            error_code="BAD_REQUEST", 
            status_code=400
        )

class DatabaseException(SmartHomeException):
    def __init__(self, detail: str):
        super().__init__(
            message=detail, 
            error_code="DATABASE_ERROR", 
            status_code=500
        )

class LogException(SmartHomeException):
    def __init__(self, detail: str):
        super().__init__(
            message=detail, 
            error_code="LOGGING_ERROR", 
            status_code=500
        )