from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, status

from ...integrations import PaymentProvider
from ...models import PaymentStatus
from ...schemas import (
    PaginatedPayments,
    PayrollGenerateRequest,
    PayrollGenerateResult,
    PaymentAttemptRead,
    PaymentCreate,
    PaymentProcessRequest,
    PaymentProcessResult,
    PaymentRead,
)
from ...services import payments as service
from ...services.payrolls import get_payroll_run_by_date
from ..dependencies import AppSettings, DBSession, get_provider, require_read, require_write

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("", response_model=PaginatedPayments, dependencies=[Depends(require_read)])
def list_payments(
    db: DBSession,
    settings: AppSettings,
    employee_id: int | None = Query(default=None, gt=0),
    payment_status: PaymentStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1),
    offset: int = Query(default=0, ge=0),
) -> PaginatedPayments:
    limit = min(limit, settings.max_page_size)
    items, total = service.list_payments(
        db, employee_id=employee_id, status=payment_status, limit=limit, offset=offset
    )
    return PaginatedPayments(
        items=[PaymentRead.model_validate(item) for item in items], total=total, limit=limit, offset=offset
    )


@router.post(
    "/generate-payroll",
    response_model=PayrollGenerateResult,
    dependencies=[Depends(require_write)],
)
def generate_payroll(payload: PayrollGenerateRequest, db: DBSession, settings: AppSettings) -> PayrollGenerateResult:
    payments, created, existing = service.generate_payroll(
        db, payload.reference_date, currency=settings.default_currency
    )
    run = get_payroll_run_by_date(db, payload.reference_date)
    assert run is not None
    return PayrollGenerateResult(
        reference_date=payload.reference_date,
        payroll_run_id=run.id,
        payroll_run_public_id=run.public_id,
        created=created,
        existing=existing,
        payment_ids=[payment.id for payment in payments],
    )


@router.post(
    "",
    response_model=PaymentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write)],
)
def create_payment(
    payload: PaymentCreate,
    db: DBSession,
    settings: AppSettings,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", max_length=120)] = None,
) -> PaymentRead:
    payment = service.create_payment(
        db,
        payload,
        idempotency_key=idempotency_key,
        default_currency=settings.default_currency,
    )
    return PaymentRead.model_validate(payment)


@router.get("/{payment_id}", response_model=PaymentRead, dependencies=[Depends(require_read)])
def get_payment(payment_id: int, db: DBSession) -> PaymentRead:
    return PaymentRead.model_validate(service.get_payment(db, payment_id))


@router.get(
    "/{payment_id}/attempts",
    response_model=list[PaymentAttemptRead],
    dependencies=[Depends(require_read)],
)
def get_attempts(payment_id: int, db: DBSession) -> list[PaymentAttemptRead]:
    return [PaymentAttemptRead.model_validate(item) for item in service.list_attempts(db, payment_id)]


@router.post(
    "/{payment_id}/process",
    response_model=PaymentProcessResult,
    dependencies=[Depends(require_write)],
)
def process_payment(
    payment_id: int,
    payload: PaymentProcessRequest,
    db: DBSession,
    settings: AppSettings,
    provider: Annotated[PaymentProvider, Depends(get_provider)],
) -> PaymentProcessResult:
    before = len(service.list_attempts(db, payment_id))
    payment, message = service.process_payment(
        db,
        payment_id,
        provider,
        dry_run=payload.dry_run,
        max_attempts=settings.provider_max_attempts,
        retry_base_seconds=settings.provider_retry_base_seconds,
    )
    after = len(service.list_attempts(db, payment_id))
    return PaymentProcessResult(
        payment=PaymentRead.model_validate(payment),
        provider=provider.name,
        dry_run=payload.dry_run,
        message=message,
        attempts=after - before,
    )


@router.post(
    "/{payment_id}/cancel",
    response_model=PaymentRead,
    dependencies=[Depends(require_write)],
)
def cancel_payment(payment_id: int, db: DBSession) -> PaymentRead:
    return PaymentRead.model_validate(service.cancel_payment(db, payment_id))
