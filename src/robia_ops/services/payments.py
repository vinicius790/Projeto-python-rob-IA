from __future__ import annotations

import hashlib
import json
import time
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..domain.payment_state import ensure_transition
from ..errors import ConflictError, InvalidStateError, NotFoundError
from ..integrations import PaymentProvider, ProviderRequest, ProviderResult
from ..models import Employee, Payment, PaymentAttempt, PaymentStatus
from ..observability.metrics import PAYMENT_PROCESSING
from ..schemas import PaymentCreate
from .audit import record_event
from .outbox import enqueue_event
from .payrolls import generate_payroll_run


def _fingerprint_request(
    *,
    employee_id: int,
    reference_date: date,
    salary: Decimal,
    meal_allowance: Decimal,
    currency: str,
) -> str:
    payload = {
        "employee_id": employee_id,
        "reference_date": reference_date.isoformat(),
        "salary": format(salary, "f"),
        "meal_allowance": format(meal_allowance, "f"),
        "currency": currency,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def create_payment(
    db: Session,
    payload: PaymentCreate,
    *,
    idempotency_key: str | None = None,
    default_currency: str = "BRL",
) -> Payment:
    employee = db.get(Employee, payload.employee_id)
    if not employee or not employee.active:
        raise NotFoundError("Colaborador ativo não encontrado")

    salary = Decimal(payload.salary if payload.salary is not None else employee.salary)
    meal_allowance = Decimal(
        payload.meal_allowance if payload.meal_allowance is not None else employee.meal_allowance
    )
    currency = payload.currency or default_currency
    request_fingerprint = _fingerprint_request(
        employee_id=employee.id,
        reference_date=payload.reference_date,
        salary=salary,
        meal_allowance=meal_allowance,
        currency=currency,
    )

    if idempotency_key:
        existing = db.scalar(select(Payment).where(Payment.idempotency_key == idempotency_key))
        if existing:
            if existing.request_fingerprint and existing.request_fingerprint != request_fingerprint:
                raise ConflictError("Idempotency-Key já utilizada com payload diferente")
            return existing

    payment = Payment(
        employee_id=employee.id,
        salary=salary,
        meal_allowance=meal_allowance,
        currency=currency,
        reference_date=payload.reference_date,
        idempotency_key=idempotency_key,
        request_fingerprint=request_fingerprint,
    )
    db.add(payment)
    try:
        db.flush()
        record_event(db, action="payment.created", entity_type="payment", entity_id=payment.id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if idempotency_key:
            existing = db.scalar(select(Payment).where(Payment.idempotency_key == idempotency_key))
            if existing:
                if existing.request_fingerprint and existing.request_fingerprint != request_fingerprint:
                    raise ConflictError("Idempotency-Key já utilizada com payload diferente") from exc
                return existing
        raise ConflictError("Pagamento duplicado ou conflito de unicidade") from exc
    db.refresh(payment)
    return payment


def get_payment(db: Session, payment_id: int) -> Payment:
    payment = db.get(Payment, payment_id)
    if not payment:
        raise NotFoundError("Pagamento não encontrado")
    return payment


def list_payments(
    db: Session,
    *,
    employee_id: int | None = None,
    status: PaymentStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Payment], int]:
    filters = []
    if employee_id:
        filters.append(Payment.employee_id == employee_id)
    if status:
        filters.append(Payment.status == status)
    stmt = (
        select(Payment)
        .where(*filters)
        .order_by(Payment.reference_date.desc(), Payment.id.desc())
        .limit(limit)
        .offset(offset)
    )
    count_stmt = select(func.count()).select_from(Payment).where(*filters)
    return list(db.scalars(stmt)), int(db.scalar(count_stmt) or 0)


def list_attempts(db: Session, payment_id: int) -> list[PaymentAttempt]:
    get_payment(db, payment_id)
    return list(
        db.scalars(
            select(PaymentAttempt)
            .where(PaymentAttempt.payment_id == payment_id)
            .order_by(PaymentAttempt.attempt_number)
        )
    )


def _next_attempt_number(db: Session, payment_id: int) -> int:
    current = db.scalar(
        select(func.max(PaymentAttempt.attempt_number)).where(PaymentAttempt.payment_id == payment_id)
    )
    return int(current or 0) + 1


def _record_attempt_start(
    db: Session,
    *,
    payment_id: int,
    attempt_number: int,
    provider: str,
    dry_run: bool,
) -> PaymentAttempt:
    attempt = PaymentAttempt(
        payment_id=payment_id,
        attempt_number=attempt_number,
        provider=provider,
        dry_run=dry_run,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def _record_attempt_finish(
    db: Session,
    attempt: PaymentAttempt,
    *,
    success: bool,
    retryable: bool,
    reference: str | None,
    message: str,
) -> None:
    attempt.success = success
    attempt.retryable = retryable
    attempt.provider_reference = reference
    attempt.message = message[:500]
    attempt.finished_at = datetime.now(timezone.utc)
    db.commit()


def process_payment(
    db: Session,
    payment_id: int,
    provider: PaymentProvider,
    *,
    dry_run: bool = True,
    max_attempts: int = 1,
    retry_base_seconds: float = 0.0,
) -> tuple[Payment, str]:
    payment = get_payment(db, payment_id)
    if payment.status not in {PaymentStatus.DRAFT, PaymentStatus.FAILED}:
        raise InvalidStateError(f"Pagamento em estado '{payment.status.value}' não pode ser processado")

    employee = db.get(Employee, payment.employee_id)
    if not employee:
        raise NotFoundError("Colaborador associado não encontrado")

    request = ProviderRequest(
        payment_id=payment.id,
        employee_reference=f"employee:{employee.public_id}",
        salary=Decimal(payment.salary),
        meal_allowance=Decimal(payment.meal_allowance),
        currency=payment.currency,
        idempotency_key=f"payment:{payment.public_id}",
    )

    if dry_run:
        attempt_number = _next_attempt_number(db, payment.id)
        attempt = _record_attempt_start(
            db,
            payment_id=payment.id,
            attempt_number=attempt_number,
            provider=provider.name,
            dry_run=True,
        )
        result = provider.process(request, dry_run=True)
        _record_attempt_finish(
            db,
            attempt,
            success=result.ok,
            retryable=result.retryable,
            reference=result.reference,
            message=result.message,
        )
        PAYMENT_PROCESSING.labels(provider.name, "dry_run", "true").inc()
        record_event(
            db,
            action="payment.dry_run",
            entity_type="payment",
            entity_id=payment.id,
            detail={"provider": provider.name, "reference": result.reference, "ok": result.ok},
        )
        db.commit()
        return payment, result.message

    ensure_transition(payment.status, PaymentStatus.QUEUED)
    payment.status = PaymentStatus.QUEUED
    payment.failure_reason = None
    record_event(
        db,
        action="payment.queued",
        entity_type="payment",
        entity_id=payment.id,
        detail={"provider": provider.name},
    )
    db.commit()
    db.refresh(payment)

    final_result: ProviderResult | None = None
    max_attempts = max(1, max_attempts)
    for retry_index in range(max_attempts):
        attempt_number = _next_attempt_number(db, payment.id)
        attempt = _record_attempt_start(
            db,
            payment_id=payment.id,
            attempt_number=attempt_number,
            provider=provider.name,
            dry_run=False,
        )
        try:
            result = provider.process(request, dry_run=False)
        except Exception as exc:  # provider boundary: never persist raw exception text
            result = ProviderResult(
                ok=False,
                reference=None,
                message=f"Provider raised {type(exc).__name__}",
                retryable=True,
            )
        _record_attempt_finish(
            db,
            attempt,
            success=result.ok,
            retryable=result.retryable,
            reference=result.reference,
            message=result.message,
        )
        final_result = result
        if result.ok or not result.retryable or retry_index == max_attempts - 1:
            break
        if retry_base_seconds:
            time.sleep(retry_base_seconds * (2**retry_index))

    assert final_result is not None
    target = PaymentStatus.PROCESSED if final_result.ok else PaymentStatus.FAILED
    ensure_transition(PaymentStatus.QUEUED, target)
    payment = get_payment(db, payment_id)
    payment.status = target
    payment.provider_reference = final_result.reference
    payment.failure_reason = None if final_result.ok else final_result.message[:500]
    payment.processed_at = datetime.now(timezone.utc) if final_result.ok else None
    action = "payment.processed" if final_result.ok else "payment.failed"
    record_event(
        db,
        action=action,
        entity_type="payment",
        entity_id=payment.id,
        detail={"provider": provider.name, "reference": final_result.reference},
    )
    enqueue_event(
        db,
        event_type=action,
        aggregate_type="payment",
        aggregate_id=payment.public_id,
        payload={
            "payment_id": payment.public_id,
            "employee_id": employee.public_id,
            "reference_date": payment.reference_date.isoformat(),
            "status": target.value,
            "currency": payment.currency,
        },
    )
    db.commit()
    db.refresh(payment)
    PAYMENT_PROCESSING.labels(provider.name, target.value, "false").inc()
    return payment, final_result.message


def cancel_payment(db: Session, payment_id: int) -> Payment:
    payment = get_payment(db, payment_id)
    if payment.status == PaymentStatus.PROCESSED:
        raise ConflictError("Pagamento processado não pode ser cancelado por esta operação")
    ensure_transition(payment.status, PaymentStatus.CANCELLED)
    payment.status = PaymentStatus.CANCELLED
    record_event(db, action="payment.cancelled", entity_type="payment", entity_id=payment.id)
    enqueue_event(
        db,
        event_type="payment.cancelled",
        aggregate_type="payment",
        aggregate_id=payment.public_id,
        payload={"payment_id": payment.public_id, "status": PaymentStatus.CANCELLED.value},
    )
    db.commit()
    db.refresh(payment)
    return payment


def generate_payroll(
    db: Session, reference_date: date, *, currency: str = "BRL"
) -> tuple[list[Payment], int, int]:
    """Backward-compatible wrapper over the first-class payroll-run orchestration."""
    _run, payments, created, existing = generate_payroll_run(db, reference_date, currency=currency)
    return payments, created, existing
