from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select

from ...models import AuditEvent
from ..dependencies import DBSession, require_admin

router = APIRouter(prefix="/audit", tags=["audit"], dependencies=[Depends(require_admin)])


class AuditEventRead(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: str
    actor: str
    request_id: str | None
    detail: dict | None
    created_at: datetime


@router.get("", response_model=list[AuditEventRead])
def list_audit_events(
    db: DBSession,
    action: str | None = Query(default=None, max_length=80),
    entity_type: str | None = Query(default=None, max_length=50),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AuditEventRead]:
    filters = []
    if action:
        filters.append(AuditEvent.action == action)
    if entity_type:
        filters.append(AuditEvent.entity_type == entity_type)
    events = list(
        db.scalars(select(AuditEvent).where(*filters).order_by(AuditEvent.id.desc()).limit(limit))
    )
    return [
        AuditEventRead(
            id=e.id,
            action=e.action,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            actor=e.actor,
            request_id=e.request_id,
            detail=json.loads(e.detail) if e.detail else None,
            created_at=e.created_at,
        )
        for e in events
    ]
