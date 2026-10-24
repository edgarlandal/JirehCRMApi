class DomainException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class AuthenticationError(DomainException):
    pass

class AuthorizationError(DomainException):
    pass

class ResourceNotFoundError(DomainException):
    pass

class DataBaseOperationError(DomainException):
    pass

