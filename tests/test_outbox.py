from robia_ops.services.outbox import enqueue_event, list_events, mark_published


def test_outbox_lifecycle(db) -> None:
    event = enqueue_event(
        db,
        event_type="demo.created",
        aggregate_type="demo",
        aggregate_id="abc",
        payload={"safe": True},
    )
    db.commit()
    db.refresh(event)
    pending, total = list_events(db)
    assert total == 1 and pending[0].event_id == event.event_id
    marked = mark_published(db, event.id)
    assert marked.published_at is not None
    pending, total = list_events(db)
    assert pending == [] and total == 0
    all_events, total = list_events(db, pending_only=False)
    assert total == 1 and all_events[0].attempts == 1
