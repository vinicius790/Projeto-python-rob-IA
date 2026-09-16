from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from robia_ops.errors import ConflictError, InvalidStateError
from robia_ops.integrations import ProviderRequest, ProviderResult, SandboxPaymentProvider
from robia_ops.models import OutboxEvent, PaymentStatus, PayrollRun
from robia_ops.schemas import EmployeeCreate, PaymentCreate
from robia_ops.services.employees import create_employee
from robia_ops.services.payments import (
    cancel_payment,
    create_payment,
    generate_payroll,
    list_attempts,
    process_payment,
)


def make_employee(db):
    return create_employee(
        db,
        EmployeeCreate(
            name="Bruno Demo",
            cpf="11144477735",
            salary=Decimal("5100.00"),
            meal_allowance=Decimal("700.00"),
        ),
    )


def test_payment_inherits_amounts_public_id_currency_and_idempotency(db) -> None:
    employee = make_employee(db)
    payload = PaymentCreate(employee_id=employee.id, reference_date=date(2026, 9, 1))
    first = create_payment(db, payload, idempotency_key="same-request")
    second = create_payment(db, payload, idempotency_key="same-request")
    assert first.id == second.id
    assert first.public_id
    assert first.salary == Decimal("5100.00")
    assert first.meal_allowance == Decimal("700.00")
    assert first.currency == "BRL"
    assert first.request_fingerprint and len(first.request_fingerprint) == 64


def test_idempotency_key_rejects_different_payload(db) -> None:
    employee = make_employee(db)
    create_payment(
        db,
        PaymentCreate(employee_id=employee.id, reference_date=date(2026, 9, 1)),
        idempotency_key="same-key",
    )
    with pytest.raises(ConflictError):
        create_payment(
            db,
            PaymentCreate(employee_id=employee.id, reference_date=date(2026, 10, 1)),
            idempotency_key="same-key",
        )


def test_dry_run_does_not_process_but_records_attempt(db) -> None:
    employee = make_employee(db)
    payment = create_payment(db, PaymentCreate(employee_id=employee.id, reference_date=date.today()))
    payment, message = process_payment(db, payment.id, SandboxPaymentProvider(), dry_run=True)
    assert payment.status == PaymentStatus.DRAFT
    assert "no transfer" in message.lower()
    attempts = list_attempts(db, payment.id)
    assert len(attempts) == 1
    assert attempts[0].dry_run is True
    assert attempts[0].success is True


def test_sandbox_process_records_attempt_outbox_and_state(db) -> None:
    employee = make_employee(db)
    payment = create_payment(db, PaymentCreate(employee_id=employee.id, reference_date=date.today()))
    payment, message = process_payment(db, payment.id, SandboxPaymentProvider(), dry_run=False)
    assert payment.status == PaymentStatus.PROCESSED
    assert payment.provider_reference and payment.provider_reference.startswith("sbx_")
    assert payment.version >= 3
    assert "no real transfer" in message.lower()
    assert len(list_attempts(db, payment.id)) == 1
    outbox = db.scalar(select(OutboxEvent).where(OutboxEvent.event_type == "payment.processed"))
    assert outbox is not None
    assert employee.public_id in outbox.payload
    with pytest.raises(InvalidStateError):
        process_payment(db, payment.id, SandboxPaymentProvider(), dry_run=False)


def test_processed_payment_cannot_be_cancelled(db) -> None:
    employee = make_employee(db)
    payment = create_payment(db, PaymentCreate(employee_id=employee.id, reference_date=date.today()))
    payment, _ = process_payment(db, payment.id, SandboxPaymentProvider(), dry_run=False)
    with pytest.raises(ConflictError):
        cancel_payment(db, payment.id)


def test_draft_can_be_cancelled_and_emits_event(db) -> None:
    employee = make_employee(db)
    payment = create_payment(db, PaymentCreate(employee_id=employee.id, reference_date=date.today()))
    cancelled = cancel_payment(db, payment.id)
    assert cancelled.status == PaymentStatus.CANCELLED
    event = db.scalar(select(OutboxEvent).where(OutboxEvent.event_type == "payment.cancelled"))
    assert event is not None


def test_generate_payroll_is_repeatable_and_creates_run(db) -> None:
    first_employee = make_employee(db)
    create_employee(
        db,
        EmployeeCreate(
            name="Second Demo",
            cpf="52998224725",
            salary=Decimal("3000.00"),
            meal_allowance=Decimal("400.00"),
        ),
    )
    first, created, existing = generate_payroll(db, date(2026, 9, 1))
    assert len(first) == 2 and created == 2 and existing == 0
    second, created, existing = generate_payroll(db, date(2026, 9, 1))
    assert len(second) == 2 and created == 0 and existing == 2
    assert {p.employee_id for p in second} >= {first_employee.id}
    run = db.scalar(select(PayrollRun))
    assert run is not None and run.payments_created == 2
    assert all(payment.payroll_run_id == run.id for payment in second)


class FlakyProvider:
    name = "flaky"

    def __init__(self) -> None:
        self.calls = 0

    def process(self, request: ProviderRequest, *, dry_run: bool = True) -> ProviderResult:
        self.calls += 1
        if self.calls == 1:
            return ProviderResult(False, None, "temporary", retryable=True)
        return ProviderResult(True, "ok-ref", "recovered")


def test_retryable_provider_failure_is_retried(db) -> None:
    employee = make_employee(db)
    payment = create_payment(db, PaymentCreate(employee_id=employee.id, reference_date=date.today()))
    provider = FlakyProvider()
    payment, message = process_payment(
        db,
        payment.id,
        provider,
        dry_run=False,
        max_attempts=3,
        retry_base_seconds=0,
    )
    assert payment.status == PaymentStatus.PROCESSED
    assert message == "recovered"
    assert provider.calls == 2
    attempts = list_attempts(db, payment.id)
    assert len(attempts) == 2
    assert attempts[0].retryable is True


class ExplodingProvider:
    name = "exploding"

    def process(self, request: ProviderRequest, *, dry_run: bool = True) -> ProviderResult:
        raise RuntimeError("secret provider detail")


def test_provider_exception_is_sanitized_and_payment_failed(db) -> None:
    employee = make_employee(db)
    payment = create_payment(db, PaymentCreate(employee_id=employee.id, reference_date=date.today()))
    payment, message = process_payment(
        db,
        payment.id,
        ExplodingProvider(),
        dry_run=False,
        max_attempts=1,
    )
    assert payment.status == PaymentStatus.FAILED
    assert message == "Provider raised RuntimeError"
    assert "secret provider detail" not in (payment.failure_reason or "")


class CapturingProvider:
    name = "capturing"

    def __init__(self) -> None:
        self.request: ProviderRequest | None = None

    def process(self, request: ProviderRequest, *, dry_run: bool = True) -> ProviderResult:
        self.request = request
        return ProviderResult(True, "captured", "ok")


def test_provider_receives_stable_payment_idempotency_key(db) -> None:
    employee = make_employee(db)
    payment = create_payment(db, PaymentCreate(employee_id=employee.id, reference_date=date.today()))
    provider = CapturingProvider()
    process_payment(db, payment.id, provider, dry_run=False)
    assert provider.request is not None
    assert provider.request.idempotency_key == f"payment:{payment.public_id}"
