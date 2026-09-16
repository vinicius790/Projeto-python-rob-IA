from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    payment_id: int
    employee_reference: str
    salary: Decimal
    meal_allowance: Decimal
    currency: str = "BRL"
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderResult:
    ok: bool
    reference: str | None
    message: str
    retryable: bool = False


class PaymentProvider(Protocol):
    name: str

    def process(self, request: ProviderRequest, *, dry_run: bool = True) -> ProviderResult: ...
