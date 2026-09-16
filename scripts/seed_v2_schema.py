"""Populate revision 0001 with representative legacy rows for migration CI."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy import create_engine, text


def main() -> None:
    engine = create_engine(os.environ["ROBIA_DATABASE_URL"])
    now = datetime.now(timezone.utc)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO employees "
                    "(name, cpf, salary, meal_allowance, active, created_at, updated_at) "
                    "VALUES (:name, :cpf, :salary, :meal, :active, :created, :updated)"
                ),
                {
                    "name": "Legacy Migration Demo",
                    "cpf": "52998224725",
                    "salary": 4200,
                    "meal": 650,
                    "active": True,
                    "created": now,
                    "updated": now,
                },
            )
            connection.execute(
                text(
                    "INSERT INTO payments "
                    "(employee_id, salary, meal_allowance, reference_date, status, idempotency_key, "
                    "provider_reference, failure_reason, created_at, processed_at) "
                    "VALUES (1, 4200, 650, '2026-09-01', 'DRAFT', 'legacy-ci', NULL, NULL, :created, NULL)"
                ),
                {"created": now},
            )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
