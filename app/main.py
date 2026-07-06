"""Composition root for the Task Tracker API.

The one module allowed to know about every layer (core/project-structure.md):
it builds settings, configures logging, wires request-id propagation,
registers the centralized exception handlers that produce the error envelope
(core/error-handling.md + core/api-design.md), and mounts the routers.
Nothing else imports from here. ASGI target: `app.main:app`.
"""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.api.v1.routers import health
from app.core.config import get_settings
from app.core.exceptions import AppError, to_error_response
from app.core.logging import configure_logging, request_id_var
from app.db.session import init_db

logger = logging.getLogger(__name__)


def _register_request_id_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        # Reuse an inbound correlation ID or mint one, per
        # core/logging-observability.md. Propagated to logs via the context
        # var and returned to the client in the response header.
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        # Every domain exception becomes the standard envelope, in one place.
        status_code, body = to_error_response(exc)
        return JSONResponse(status_code=status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Reshape FastAPI's default 422 into the same error envelope so
        # validation failures match every other error (idioms.md).
        logger.warning("request_validation_error")
        body = {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed.",
                "details": {"errors": exc.errors()},
            }
        }
        return JSONResponse(status_code=422, content=jsonable_encoder(body))


def create_app() -> FastAPI:
    """Application factory — a fresh app per call so tests can override deps."""
    settings = get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Convenience: create tables on boot. A real service runs migrations
        # (e.g. Alembic) instead — see README.
        init_db()
        logger.info("app_started", extra={"environment": settings.environment})
        yield

    app = FastAPI(title="Task Tracker API", version="1.0.0", lifespan=lifespan)

    _register_request_id_middleware(app)
    _register_exception_handlers(app)

    app.include_router(health.router)  # /health, /ready — unversioned
    app.include_router(api_router)     # /v1/...

    return app


app = create_app()
