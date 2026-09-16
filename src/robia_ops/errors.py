class RobIAError(Exception):
    """Base domain error."""


class NotFoundError(RobIAError):
    pass


class ConflictError(RobIAError):
    pass


class InvalidStateError(RobIAError):
    pass
