from app.core.logging_config import setup_logging

setup_logging()

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.routes import admin, auth, healthy, users
from app.api.routes import (
    appointments,
    contacts,
    customers,
    interactions,
    services,
    ticket_comments,
    tickets,
)
from app.core.config import settings
from app.core.error_handlers import register_exception_handler
from app.core.middleware import (
    LoggingAndCorrelationMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.rate_limit import limiter


class LoggedFastAPI(FastAPI):
    def build_middleware_stack(self):
        return LoggingAndCorrelationMiddleware(super().build_middleware_stack())


def create_app():
    app = LoggedFastAPI(title=settings.PROJECT_NAME)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "Accept",
            "X-Requested-With",
            "X-Request-ID",
        ],
        expose_headers=["Content-Disposition", "X-Request-ID"],
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

    app.state.limiter = limiter

    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    register_exception_handler(app)

    api_router = APIRouter(prefix="/api/v1")

    api_router.include_router(healthy.router)
    api_router.include_router(auth.router)
    api_router.include_router(admin.router)
    api_router.include_router(users.router)
    api_router.include_router(customers.router)
    api_router.include_router(contacts.router)
    api_router.include_router(services.router)
    api_router.include_router(interactions.router)
    api_router.include_router(appointments.router)
    api_router.include_router(tickets.router)
    api_router.include_router(ticket_comments.router)
    app.include_router(api_router)

    return app


app = create_app()
