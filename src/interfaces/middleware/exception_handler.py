"""Global exception handlers for FastAPI."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.core.exceptions.application import ApplicationError, UseCaseError
from src.core.exceptions.domain import DomainError, EntityNotFoundError, ValidationError
from src.core.exceptions.infrastructure import DatabaseError, ExternalServiceError, InfrastructureError
from src.core.logging.logger import get_logger

logger = get_logger("quantiquan.middleware.exception_handler")


def setup_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers for the FastAPI app.

    Args:
        app: FastAPI application instance.
    """
    app.add_exception_handler(DomainError, handle_domain_error)
    app.add_exception_handler(ValidationError, handle_validation_error)
    app.add_exception_handler(EntityNotFoundError, handle_not_found_error)
    app.add_exception_handler(ApplicationError, handle_application_error)
    app.add_exception_handler(InfrastructureError, handle_infrastructure_error)
    app.add_exception_handler(Exception, handle_generic_error)


def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
    """Handle domain errors (422)."""
    logger.warning(
        "Domain error",
        error=str(exc),
        code=exc.code,
        detail=exc.detail,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": exc.code, "message": exc.message, "detail": exc.detail},
    )


def handle_validation_error(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle validation errors (422)."""
    logger.warning(
        "Validation error",
        error=str(exc),
        field=exc.detail.get("field"),
        path=request.url.path,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "validation_error", "message": exc.message, "field": exc.detail.get("field")},
    )


def handle_not_found_error(request: Request, exc: EntityNotFoundError) -> JSONResponse:
    """Handle not found errors (404)."""
    logger.info("Entity not found", error=str(exc), entity=exc.detail.get("entity"), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": "not_found", "message": exc.message},
    )


def handle_application_error(request: Request, exc: ApplicationError) -> JSONResponse:
    """Handle application errors (500)."""
    logger.error(
        "Application error",
        error=str(exc),
        code=exc.code,
        detail=exc.detail,
        path=request.url.path,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "application_error", "message": "An internal error occurred"},
    )


def handle_infrastructure_error(request: Request, exc: InfrastructureError) -> JSONResponse:
    """Handle infrastructure errors (503)."""
    logger.error(
        "Infrastructure error",
        error=str(exc),
        code=exc.code,
        detail=exc.detail,
        path=request.url.path,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"error": "service_unavailable", "message": "A downstream service is unavailable"},
    )


def handle_generic_error(request: Request, exc: Exception) -> JSONResponse:
    """Handle any unhandled exceptions (500)."""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        exc_type=exc.__class__.__name__,
        path=request.url.path,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "internal_error", "message": "An unexpected error occurred"},
    )