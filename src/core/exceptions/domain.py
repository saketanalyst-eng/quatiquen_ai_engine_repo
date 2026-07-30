"""Domain layer exceptions.

These exceptions represent violations of business rules, invalid entity
states, or value object constraints.
"""


class DomainError(Exception):
    """Base exception for domain layer errors.

    Raised when business rules are violated or entity state is invalid.
    """

    def __init__(self, message: str, code: str = "DOMAIN_ERROR", detail: dict = None) -> None:
        """Initialize domain error.

        Args:
            message: Human-readable error message.
            code: Error code for categorization.
            detail: Additional error context data.
        """
        self.message = message
        self.code = code
        self.detail = detail or {}
        super().__init__(message)


class ValidationError(DomainError):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: str = None, value=None) -> None:
        """Initialize validation error.

        Args:
            message: Error description.
            field: Field that failed validation.
            value: Invalid value.
        """
        detail = {}
        if field:
            detail["field"] = field
        if value is not None:
            detail["value"] = str(value)
        super().__init__(message, code="VALIDATION_ERROR", detail=detail)


class InvalidValueObjectError(DomainError):
    """Raised when a value object is constructed with invalid data."""

    def __init__(self, message: str, value_object: str = None) -> None:
        """Initialize invalid value object error.

        Args:
            message: Error description.
            value_object: Name of the invalid value object.
        """
        detail = {"value_object": value_object} if value_object else {}
        super().__init__(message, code="INVALID_VALUE_OBJECT", detail=detail)


class InvalidEntityStateError(DomainError):
    """Raised when an entity transitions to an invalid state."""

    def __init__(self, message: str, entity: str = None, state: str = None) -> None:
        """Initialize invalid entity state error.

        Args:
            message: Error description.
            entity: Name of the entity.
            state: Invalid state attempted.
        """
        detail = {}
        if entity:
            detail["entity"] = entity
        if state:
            detail["state"] = state
        super().__init__(message, code="INVALID_ENTITY_STATE", detail=detail)


class EntityNotFoundError(DomainError):
    """Raised when an entity cannot be found."""

    def __init__(self, entity: str, identifier: str) -> None:
        """Initialize entity not found error.

        Args:
            entity: Entity type name.
            identifier: Entity identifier.
        """
        message = f"{entity} with identifier {identifier} not found"
        super().__init__(message, code="ENTITY_NOT_FOUND", detail={"entity": entity, "identifier": identifier})