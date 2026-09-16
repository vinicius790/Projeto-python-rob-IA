from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..errors import ConflictError, NotFoundError
from ..models import Employee, Payment, PayrollRun, PayrollRunStatus
from .audit import record_event
from .outbox import enqueue_event


def get_payroll_run(db: Session, run_id: int) -> PayrollRun:
    run = db.get(PayrollRun, run_id)
    if not run:
        raise NotFoundError("Execução de folha não encontrada")
    return run


def get_payroll_run_by_date(db: Session, reference_date: date) -> PayrollRun | None:
    return db.scalar(select(PayrollRun).where(PayrollRun.reference_date == reference_date))


def list_payroll_runs(
    db: Session, *, limit: int = 50, offset: int = 0
) -> tuple[list[PayrollRun], int]:
    stmt = select(PayrollRun).order_by(PayrollRun.reference_date.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count()).select_from(PayrollRun)
    return list(db.scalars(stmt)), int(db.scalar(count_stmt) or 0)


def generate_payroll_run(
    db: Session,
    reference_date: date,
    *,
    currency: str = "BRL",
) -> tuple[PayrollRun, list[Payment], int, int]:
    existing_run = get_payroll_run_by_date(db, reference_date)
    if existing_run and existing_run.status == PayrollRunStatus.COMPLETED:
        payments = list(
            db.scalars(
                select(Payment)
                .where(Payment.payroll_run_id == existing_run.id)
                .order_by(Payment.employee_id)
            )
        )
        return existing_run, payments, 0, len(payments)

    if existing_run:
        run = existing_run
    else:
        run = PayrollRun(reference_date=reference_date, status=PayrollRunStatus.RUNNING)
        db.add(run)
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            raise ConflictError("Já existe uma execução de folha para esta referência") from exc

    employees = list(db.scalars(select(Employee).where(Employee.active.is_(True)).order_by(Employee.id)))
    keys = [f"payroll:{reference_date.isoformat()}:{employee.id}" for employee in employees]
    existing_by_key = {
        item.idempotency_key: item
        for item in db.scalars(select(Payment).where(Payment.idempotency_key.in_(keys)))
        if item.idempotency_key
    } if keys else {}

    payments: list[Payment] = []
    created = 0
    existing = 0
    for employee, key in zip(employees, keys):
        found = existing_by_key.get(key)
        if found:
            if found.payroll_run_id is None:
                found.payroll_run_id = run.id
            payments.append(found)
            existing += 1
            continue
        payment = Payment(
            employee_id=employee.id,
            payroll_run_id=run.id,
            salary=employee.salary,
            meal_allowance=employee.meal_allowance,
            currency=currency,
            reference_date=reference_date,
            idempotency_key=key,
            request_fingerprint=None,
        )
        db.add(payment)
        db.flush()
        record_event(
            db,
            action="payment.generated",
            entity_type="payment",
            entity_id=payment.id,
            detail={"reference_date": reference_date.isoformat(), "payroll_run_id": run.id},
        )
        payments.append(payment)
        created += 1

    run.status = PayrollRunStatus.COMPLETED
    run.employees_total = len(employees)
    run.payments_created = created
    run.payments_existing = existing
    run.completed_at = datetime.now(timezone.utc)
    record_event(
        db,
        action="payroll.completed",
        entity_type="payroll_run",
        entity_id=run.id,
        detail={"reference_date": reference_date.isoformat(), "created": created, "existing": existing},
    )
    enqueue_event(
        db,
        event_type="payroll.completed",
        aggregate_type="payroll_run",
        aggregate_id=run.public_id,
        payload={
            "payroll_run_id": run.public_id,
            "reference_date": reference_date.isoformat(),
            "employees_total": len(employees),
            "payments_created": created,
            "payments_existing": existing,
        },
    )
    db.commit()
    db.refresh(run)
    for payment in payments:
        db.refresh(payment)
    return run, payments, created, existing
