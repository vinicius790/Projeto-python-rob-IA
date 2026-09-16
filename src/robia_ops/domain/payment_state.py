from __future__ import annotations

from ..errors import InvalidStateError
from ..models import PaymentStatus

_ALLOWED: dict[PaymentStatus, frozenset[PaymentStatus]] = {
    PaymentStatus.DRAFT: frozenset({PaymentStatus.QUEUED, PaymentStatus.CANCELLED}),
    PaymentStatus.QUEUED: frozenset({PaymentStatus.PROCESSED, PaymentStatus.FAILED}),
    PaymentStatus.FAILED: frozenset({PaymentStatus.QUEUED, PaymentStatus.CANCELLED}),
    PaymentStatus.PROCESSED: frozenset(),
    PaymentStatus.CANCELLED: frozenset(),
}


def ensure_transition(current: PaymentStatus, target: PaymentStatus) -> None:
    if target not in _ALLOWED[current]:
        raise InvalidStateError(
            f"Transição de pagamento inválida: '{current.value}' -> '{target.value}'"
        )


def can_transition(current: PaymentStatus, target: PaymentStatus) -> bool:
    return target in _ALLOWED[current]
