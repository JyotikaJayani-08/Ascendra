"""
Ascendra — Main Application Entry Point.
"""

import logging

from fastapi import FastAPI, Request, status, APIRouter
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.config import settings
from app.core.exceptions import AscendraException
from app.core.middleware import setup_middleware

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.limiter import limiter

# Routers
from app.auth.router import router as auth_router
from app.users.router import router as users_router
from app.resumes.router import router as resumes_router
from app.applications.router import router as applications_router
from app.jobs.router import router as jobs_router
from app.contacts.router import router as contacts_router
from app.ai.router import router as ai_router
from app.email.router import router as email_router
from app.dashboard.router import router as dashboard_router
from app.notifications.router import router as notifications_router
from app.notes.router import router as notes_router
from app.auth.email_config_router import router as email_config_router
from app.auth.google_oauth_router import router as google_oauth_router

from app.core.logging import setup_logging

# Initialize centralized logging (file + console handlers)
setup_logging(
    log_filename="backend.log",
    level=logging.INFO if not settings.is_production else logging.WARNING,
)
logger = logging.getLogger("ascendra")

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.cache import init_redis, close_redis
    await init_redis()

    yield

    await close_redis()


app = FastAPI(
    title="Ascendra API",
    version="1.0.0",
    description="Modular monolith API for Ascendra Career Platform.",
    lifespan=lifespan,
)

# Register Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

setup_middleware(app)

# API v1 Router Namespace
api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(resumes_router)
api_v1_router.include_router(applications_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(contacts_router)
api_v1_router.include_router(ai_router)
api_v1_router.include_router(email_router)
api_v1_router.include_router(dashboard_router)
api_v1_router.include_router(notifications_router)
api_v1_router.include_router(notes_router)
api_v1_router.include_router(email_config_router)
api_v1_router.include_router(google_oauth_router)

# Register /api/v1 routes
app.include_router(api_v1_router)


@app.exception_handler(AscendraException)
async def ascendra_exception_handler(request: Request, exc: AscendraException):
    """Format custom exceptions into standard RFC 7807 JSON responses."""
    code = exc.detail.get("code", "ERROR") if isinstance(exc.detail, dict) else "ERROR"
    message = exc.detail.get("message", str(exc.detail)) if isinstance(exc.detail, dict) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": "about:blank",
            "title": code,
            "status": exc.status_code,
            "detail": message,
            "instance": request.url.path,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Format Pydantic validation errors securely using RFC 7807."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "type": "about:blank",
            "title": "VALIDATION_ERROR",
            "status": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "detail": "Invalid input parameters.",
            "instance": request.url.path,
            "errors": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all for internal server errors — never leak tracebacks to clients."""
    logger.error(f"Unhandled Internal Error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "type": "about:blank",
            "title": "INTERNAL_SERVER_ERROR",
            "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "detail": "An unexpected error occurred. Please try again later.",
            "instance": request.url.path,
        },
    )


@app.get("/health", tags=["System"])
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "environment": settings.ENVIRONMENT}

