class ApplicationError(Exception):
    status_code = 400
    code = "application_error"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(ApplicationError):
    status_code = 404
    code = "not_found"


class ConflictError(ApplicationError):
    status_code = 409
    code = "conflict"


class UnauthorizedError(ApplicationError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(ApplicationError):
    status_code = 403
    code = "forbidden"


class ValidationError(ApplicationError):
    status_code = 422
    code = "validation_error"
