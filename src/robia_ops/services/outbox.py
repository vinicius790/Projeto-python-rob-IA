from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..errors import NotFoundError
from ..models import OutboxEvent


def enqueue_event(
    db: Session,
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str | int,
    payload: dict[str, Any],
) -> OutboxEvent:
    event = OutboxEvent(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=str(aggregate_id),
        payload=json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str),
    )
    db.add(event)
    return event


def list_events(
    db: Session,
    *,
    pending_only: bool = True,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[OutboxEvent], int]:
    filters = [OutboxEvent.published_at.is_(None)] if pending_only else []
    stmt = (
        select(OutboxEvent)
        .where(*filters)
        .order_by(OutboxEvent.id)
        .limit(limit)
        .offset(offset)
    )
    count_stmt = select(func.count()).select_from(OutboxEvent).where(*filters)
    return list(db.scalars(stmt)), int(db.scalar(count_stmt) or 0)


def mark_published(db: Session, event_id: int) -> OutboxEvent:
    event = db.get(OutboxEvent, event_id)
    if not event:
        raise NotFoundError("Evento de outbox não encontrado")
    if event.published_at is None:
        event.published_at = datetime.now(timezone.utc)
        event.attempts += 1
        db.commit()
        db.refresh(event)
    return event
