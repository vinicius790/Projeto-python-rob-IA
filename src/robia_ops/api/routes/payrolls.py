from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from ...schemas import PaginatedPayrollRuns, PayrollGenerateRequest, PayrollGenerateResult, PayrollRunRead
from ...services.payrolls import generate_payroll_run, get_payroll_run, list_payroll_runs
from ..dependencies import AppSettings, DBSession, require_read, require_write

router = APIRouter(prefix="/payroll-runs", tags=["payroll-runs"])


@router.get("", response_model=PaginatedPayrollRuns, dependencies=[Depends(require_read)])
def list_runs(
    db: DBSession,
    settings: AppSettings,
    limit: int = Query(default=50, ge=1),
    offset: int = Query(default=0, ge=0),
) -> PaginatedPayrollRuns:
    limit = min(limit, settings.max_page_size)
    items, total = list_payroll_runs(db, limit=limit, offset=offset)
    return PaginatedPayrollRuns(
        items=[PayrollRunRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{run_id}", response_model=PayrollRunRead, dependencies=[Depends(require_read)])
def get_run(run_id: int, db: DBSession) -> PayrollRunRead:
    return PayrollRunRead.model_validate(get_payroll_run(db, run_id))


@router.post(
    "",
    response_model=PayrollGenerateResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write)],
)
def create_run(payload: PayrollGenerateRequest, db: DBSession, settings: AppSettings) -> PayrollGenerateResult:
    run, payments, created, existing = generate_payroll_run(
        db, payload.reference_date, currency=settings.default_currency
    )
    return PayrollGenerateResult(
        reference_date=run.reference_date,
        payroll_run_id=run.id,
        payroll_run_public_id=run.public_id,
        created=created,
        existing=existing,
        payment_ids=[payment.id for payment in payments],
    )
