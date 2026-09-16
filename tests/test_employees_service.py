from decimal import Decimal

import pytest
from sqlalchemy import select

from robia_ops.errors import ConflictError, NotFoundError
from robia_ops.models import AuditEvent
from robia_ops.schemas import EmployeeCreate, EmployeeRead, EmployeeUpdate
from robia_ops.services.employees import (
    create_employee,
    deactivate_employee,
    get_employee,
    get_employee_by_cpf,
    list_employees,
    update_employee,
)


def employee_payload() -> EmployeeCreate:
    return EmployeeCreate(
        name="  Ana   Demo  ",
        cpf="529.982.247-25",
        salary=Decimal("4200.00"),
        meal_allowance=Decimal("650.00"),
    )


def test_create_get_and_minimize_cpf(db) -> None:
    employee = create_employee(db, employee_payload(), pii_key="test-secret")
    assert employee.id
    assert employee.public_id
    assert employee.name == "Ana Demo"
    assert employee.cpf_last2 == "25"
    assert employee.cpf_fingerprint != "52998224725"
    assert len(employee.cpf_fingerprint) == 64
    assert "52998224725" not in repr(employee.__dict__)
    assert get_employee(db, employee.id).id == employee.id
    assert get_employee_by_cpf(db, "52998224725", pii_key="test-secret").id == employee.id
    assert EmployeeRead.from_model(employee).cpf == "***.***.***-25"
    assert db.scalar(select(AuditEvent.action)) == "employee.created"


def test_duplicate_cpf_is_conflict(db) -> None:
    create_employee(db, employee_payload())
    with pytest.raises(ConflictError):
        create_employee(db, employee_payload())


def test_search_only_uses_non_sensitive_name(db) -> None:
    employee = create_employee(db, employee_payload())
    items, total = list_employees(db, search="Ana")
    assert total == 1 and items[0].id == employee.id
    items, total = list_employees(db, search="529982")
    assert total == 0 and items == []


def test_update_deactivate_and_idempotent_deactivation(db) -> None:
    employee = create_employee(db, employee_payload())
    updated = update_employee(db, employee.id, EmployeeUpdate(salary=Decimal("4500.00")))
    assert updated.salary == Decimal("4500.00")
    assert updated.version >= 2

    deactivated = deactivate_employee(db, employee.id)
    assert deactivated.active is False
    again = deactivate_employee(db, employee.id)
    assert again.active is False
    items, total = list_employees(db, active=True)
    assert total == 0 and items == []


def test_missing_employee(db) -> None:
    with pytest.raises(NotFoundError):
        get_employee(db, 999)
