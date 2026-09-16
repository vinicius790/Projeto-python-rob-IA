from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..errors import ConflictError, NotFoundError
from ..models import Employee
from ..schemas import EmployeeCreate, EmployeeUpdate
from ..security.pii import cpf_last2, fingerprint_cpf
from .audit import record_event


def _pii_secret(override: str | None = None) -> str:
    return override or get_settings().pii_key.get_secret_value()


def create_employee(db: Session, payload: EmployeeCreate, *, pii_key: str | None = None) -> Employee:
    secret = _pii_secret(pii_key)
    employee = Employee(
        name=payload.name,
        cpf_fingerprint=fingerprint_cpf(payload.cpf, secret),
        cpf_last2=cpf_last2(payload.cpf),
        salary=payload.salary,
        meal_allowance=payload.meal_allowance,
    )
    db.add(employee)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Já existe colaborador com este CPF") from exc
    record_event(db, action="employee.created", entity_type="employee", entity_id=employee.id)
    db.commit()
    db.refresh(employee)
    return employee


def get_employee(db: Session, employee_id: int) -> Employee:
    employee = db.get(Employee, employee_id)
    if not employee:
        raise NotFoundError("Colaborador não encontrado")
    return employee


def get_employee_by_cpf(db: Session, cpf: str, *, pii_key: str | None = None) -> Employee | None:
    digest = fingerprint_cpf(cpf, _pii_secret(pii_key))
    return db.scalar(select(Employee).where(Employee.cpf_fingerprint == digest))


def list_employees(
    db: Session,
    *,
    search: str | None = None,
    active: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Employee], int]:
    filters = []
    if search:
        # Intentionally search only non-sensitive display data.  CPF lookup uses
        # a keyed exact-match fingerprint through get_employee_by_cpf.
        filters.append(Employee.name.ilike(f"%{search.strip()}%"))
    if active is not None:
        filters.append(Employee.active.is_(active))

    stmt = select(Employee).where(*filters).order_by(Employee.name, Employee.id).limit(limit).offset(offset)
    count_stmt = select(func.count()).select_from(Employee).where(*filters)
    return list(db.scalars(stmt)), int(db.scalar(count_stmt) or 0)


def update_employee(db: Session, employee_id: int, payload: EmployeeUpdate) -> Employee:
    employee = get_employee(db, employee_id)
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(employee, key, value)
    record_event(
        db,
        action="employee.updated",
        entity_type="employee",
        entity_id=employee.id,
        detail={"fields": sorted(changes)},
    )
    db.commit()
    db.refresh(employee)
    return employee


def deactivate_employee(db: Session, employee_id: int) -> Employee:
    employee = get_employee(db, employee_id)
    if employee.active:
        employee.active = False
        record_event(db, action="employee.deactivated", entity_type="employee", entity_id=employee.id)
        db.commit()
        db.refresh(employee)
    return employee
