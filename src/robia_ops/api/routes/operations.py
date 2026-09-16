from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ...schemas import OutboxEventRead
from ...services.outbox import list_events, mark_published
from ..dependencies import AppSettings, DBSession, require_admin

router = APIRouter(prefix="/operations", tags=["operations"], dependencies=[Depends(require_admin)])


@router.get("/outbox", response_model=list[OutboxEventRead])
def outbox_events(
    db: DBSession,
    settings: AppSettings,
    pending_only: bool = True,
    limit: int = Query(default=100, ge=1),
    offset: int = Query(default=0, ge=0),
) -> list[OutboxEventRead]:
    limit = min(limit, settings.max_page_size)
    events, _total = list_events(db, pending_only=pending_only, limit=limit, offset=offset)
    return [OutboxEventRead.model_validate(item) for item in events]


@router.post("/outbox/{event_id}/ack", response_model=OutboxEventRead)
def acknowledge_outbox(event_id: int, db: DBSession) -> OutboxEventRead:
    return OutboxEventRead.model_validate(mark_published(db, event_id))
