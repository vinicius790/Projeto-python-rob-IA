from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from ..models import AuditEvent
from ..observability.context import get_request_id


def record_event(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str | int,
    actor: str = "system",
    detail: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        actor=actor,
        request_id=get_request_id(),
        detail=json.dumps(detail, ensure_ascii=False, sort_keys=True, default=str) if detail else None,
    )
    db.add(event)
    return event
