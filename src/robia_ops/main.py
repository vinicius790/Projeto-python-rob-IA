from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from sqlalchemy.orm.exc import StaleDataError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .api.router import api_router
from .config import Settings, get_settings
from .errors import ConflictError, InvalidStateError, NotFoundError
from .logging_config import configure_logging
from .middleware import RequestBodyLimitMiddleware
from .observability.context import request_id_var
from .observability.metrics import HTTP_DURATION, HTTP_REQUESTS
from .web.routes import router as web_router

logger = logging.getLogger("robia.request")


def _error_payload(code: str, detail: str, request_id: str | None) -> dict[str, object]:
    return {"detail": detail, "error": {"code": code, "request_id": request_id}}


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    docs_url = "/docs" if settings.docs_enabled else None
    redoc_url = "/redoc" if settings.docs_enabled else None
    openapi_url = "/openapi.json" if settings.docs_enabled else None
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Workforce and payment operations platform with safe sandbox processing, "
            "auditability, operational outbox, scoped API keys and explainable analytics."
        ),
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )
    app.state.settings = settings

    app.add_middleware(RequestBodyLimitMiddleware, max_bytes=settings.max_request_bytes)
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts_list)
    if settings.allowed_origins_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_origins_list,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["Content-Type", "X-API-Key", "X-Request-ID", "Idempotency-Key"],
        )

    if settings.dashboard_enabled:
        static_dir = Path(__file__).resolve().parent / "web" / "static"
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.middleware("http")
    async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
            elapsed = time.perf_counter() - started
            route_obj = request.scope.get("route")
            route = getattr(route_obj, "path", "__unmatched__")
            HTTP_REQUESTS.labels(request.method, route, str(response.status_code)).inc()
            HTTP_DURATION.labels(request.method, route).observe(elapsed)
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
            response.headers[
                "Content-Security-Policy"
            ] = "default-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
            if request.url.path.startswith("/api/"):
                response.headers["Cache-Control"] = "no-store"
            if settings.is_production:
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            logger.info(
                "request.completed",
                extra={
                    "context": {
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "route": route,
                        "status_code": response.status_code,
                        "duration_ms": round(elapsed * 1000, 2),
                    }
                },
            )
            return response
        finally:
            request_id_var.reset(token)

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=_error_payload("not_found", str(exc), request_id_var.get()),
        )

    @app.exception_handler(ConflictError)
    async def conflict_handler(_request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content=_error_payload("conflict", str(exc), request_id_var.get()),
        )

    @app.exception_handler(InvalidStateError)
    async def invalid_state_handler(_request: Request, exc: InvalidStateError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_error_payload("invalid_state", str(exc), request_id_var.get()),
        )

    @app.exception_handler(StaleDataError)
    async def stale_data_handler(_request: Request, _exc: StaleDataError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content=_error_payload(
                "concurrent_update",
                "O recurso foi alterado por outra operação; recarregue e tente novamente",
                request_id_var.get(),
            ),
        )

    @app.exception_handler(Exception)
    async def unexpected_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("request.unhandled_error", extra={"context": {"exception_type": type(exc).__name__}})
        return JSONResponse(
            status_code=500,
            content=_error_payload(
                "internal_error",
                "Erro interno inesperado",
                request_id_var.get(),
            ),
        )

    app.include_router(api_router)
    if settings.dashboard_enabled:
        app.include_router(web_router)
    else:

        @app.get("/", include_in_schema=False)
        def service_root() -> dict[str, str]:
            return {"service": settings.app_name, "version": settings.app_version, "status": "ok"}

    return app


app = create_app()
