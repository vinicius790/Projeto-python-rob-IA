from datetime import date
from decimal import Decimal

from robia_ops.schemas import EmployeeCreate, PaymentCreate
from robia_ops.services.analytics import detect_anomalies, monthly_payroll, summary
from robia_ops.services.employees import create_employee
from robia_ops.services.payments import create_payment


def test_empty_summary_and_monthly(db) -> None:
    result = summary(db)
    assert result.employees_total == 0
    assert result.payments_total == 0
    assert result.failed_total == 0
    assert result.payroll_total == Decimal("0.00")
    assert monthly_payroll(db) == []


def test_summary_monthly_and_fallback_anomalies(db) -> None:
    employee = create_employee(
        db,
        EmployeeCreate(name="Carla Demo", cpf="12345678909", salary="3900", meal_allowance="600"),
    )
    for index, salary in enumerate(("3900", "3920", "3880"), start=1):
        create_payment(
            db,
            PaymentCreate(
                employee_id=employee.id,
                reference_date=date(2026, 3, index),
                salary=salary,
                meal_allowance="600",
            ),
        )
    stats = summary(db)
    assert stats.employees_total == 1
    assert stats.payments_total == 3
    assert stats.average_payment > 0
    monthly = monthly_payroll(db)
    assert len(monthly) == 1 and monthly[0].payments == 3 and monthly[0].month == "2026-03"
    results = detect_anomalies(db)
    assert len(results) == 3
    assert all(item.model == "statistical_fallback" for item in results)


def test_isolation_forest_path_when_enough_data(db) -> None:
    employee = create_employee(
        db,
        EmployeeCreate(name="Data Demo", cpf="39053344705", salary="3000", meal_allowance="500"),
    )
    for index in range(8):
        create_payment(
            db,
            PaymentCreate(
                employee_id=employee.id,
                reference_date=date(2026, 1, index + 1),
                salary=Decimal("3000") + index,
                meal_allowance="500",
            ),
        )
    results = detect_anomalies(db)
    assert len(results) == 8
    assert results[0].model in {"isolation_forest", "statistical_fallback"}
