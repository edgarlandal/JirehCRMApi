import traceback

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    DataBaseOperationError,
    ResourceNotFoundError,
)


def register_exception_handler(app: FastAPI) -> None:

    # 1. Validation Errors (Errores de entrada Pydantic / Query / Path)
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        errors = []

        for err in exc.errors():
            loc = " -> ".join([str(x) for x in err.get("loc", [])])
            msg = err.get("msg", "Invalid data")
            errors.append({"field": loc, "message": msg})

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"error": "Validation Error", "details": errors},
        )

    # 2. Authentication Errors
    @app.exception_handler(AuthenticationError)
    async def auth_exception_handler(request: Request, exc: AuthenticationError):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Faild Authentication", "message": exc.message},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Authorization Errors
    @app.exception_handler(AuthorizationError)
    async def forbidden_exception_handler(request: Request, exc: AuthorizationError):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": "Denieded Access", "message": exc.message},
        )

    # 4. Resource Not Found
    @app.exception_handler(ResourceNotFoundError)
    async def not_found_exption_handler(request: Request, exc: ResourceNotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Not found resource", "message": exc.message},
        )

    # 5. Database Errors (SQLAlchemyError)
    @app.exception_handler(SQLAlchemyError)
    @app.exception_handler(DataBaseOperationError)
    async def database_exception_handler(request: Request, exc: Exception):
        logger.error(
            "database_error", event="error.database", exception_type=type(exc).__name__
        )
        # print("DETALLE ERROR BD:", str(exc.orig), flush=True)
        print(f"SQLAlchemy error: {type(exc).__name__}: {exc}", flush=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Error in database",
                "message": "There was a problem processing the request in storage.",
            },
        )

    # 6. Unexpected / Unhandled Errors (500 Internal Server Error)
    @app.exception_handler(Exception)
    async def unexpected_exception_handler(request: Request, exc: Exception):
        traceback.print_exception(
            type(exc),
            exc,
            exc.__traceback__,
        )

        logger.error(
            "unhandled_error",
            exc_info=True,
            extra={
                "event": "error.unhandled",
                "exception_type": type(exc).__name__,
                "error_message": str(exc),
            },
        )
