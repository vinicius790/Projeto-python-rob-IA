import pytest

from robia_ops.domain.payment_state import can_transition, ensure_transition
from robia_ops.errors import InvalidStateError
from robia_ops.models import PaymentStatus


def test_payment_state_machine() -> None:
    assert can_transition(PaymentStatus.DRAFT, PaymentStatus.QUEUED)
    assert can_transition(PaymentStatus.FAILED, PaymentStatus.CANCELLED)
    assert not can_transition(PaymentStatus.PROCESSED, PaymentStatus.CANCELLED)
    ensure_transition(PaymentStatus.QUEUED, PaymentStatus.PROCESSED)
    with pytest.raises(InvalidStateError):
        ensure_transition(PaymentStatus.CANCELLED, PaymentStatus.DRAFT)
