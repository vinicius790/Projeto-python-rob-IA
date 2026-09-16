from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ..dependencies import AppSettings, require_read

router = APIRouter(tags=["observability"])


@router.get("/metrics", include_in_schema=False, dependencies=[Depends(require_read)])
def metrics(settings: AppSettings) -> Response:
    if not settings.enable_metrics:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metrics disabled")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
