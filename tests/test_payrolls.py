from datetime import date

import pytest

from robia_ops.errors import NotFoundError
from robia_ops.models import PayrollRunStatus
from robia_ops.schemas import EmployeeCreate
from robia_ops.services.employees import create_employee
from robia_ops.services.payrolls import generate_payroll_run, get_payroll_run, list_payroll_runs


def test_empty_payroll_run_is_completed_and_repeatable(db) -> None:
    run, payments, created, existing = generate_payroll_run(db, date(2026, 1, 1))
    assert run.status == PayrollRunStatus.COMPLETED
    assert run.employees_total == 0
    assert payments == [] and created == 0 and existing == 0
    same, payments, created, existing = generate_payroll_run(db, date(2026, 1, 1))
    assert same.id == run.id
    assert payments == [] and created == 0 and existing == 0


def test_list_and_get_payroll_runs(db) -> None:
    create_employee(
        db,
        EmployeeCreate(name="Payroll User", cpf="52998224725", salary="1000", meal_allowance="100"),
    )
    run, _, _, _ = generate_payroll_run(db, date(2026, 2, 1))
    items, total = list_payroll_runs(db)
    assert total == 1 and items[0].id == run.id
    assert get_payroll_run(db, run.id).public_id == run.public_id
    with pytest.raises(NotFoundError):
        get_payroll_run(db, 999)
