from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text

from ...schemas import HealthResponse, MetaResponse
from ..dependencies import AppSettings, DBSession, require_read

router = APIRouter(tags=["health"])


@router.get("/live", response_model=HealthResponse)
def liveness(settings: AppSettings) -> HealthResponse:
    return HealthResponse(status="alive", version=settings.app_version, database="not_checked")


@router.get("/health", response_model=HealthResponse)
def health(db: DBSession, settings: AppSettings) -> HealthResponse:
    db.execute(text("SELECT 1"))
    return HealthResponse(status="ok", version=settings.app_version, database="ok")


@router.get("/ready", response_model=HealthResponse)
def readiness(db: DBSession, settings: AppSettings) -> HealthResponse:
    db.execute(text("SELECT 1"))
    return HealthResponse(status="ready", version=settings.app_version, database="ok")


@router.get("/meta", response_model=MetaResponse, dependencies=[Depends(require_read)])
def meta(settings: AppSettings) -> MetaResponse:
    return MetaResponse(
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.env,
        auth_enabled=settings.auth_enabled,
        provider=settings.provider,
        dashboard_enabled=settings.dashboard_enabled,
        docs_enabled=settings.docs_enabled,
        metrics_enabled=settings.enable_metrics,
    )
