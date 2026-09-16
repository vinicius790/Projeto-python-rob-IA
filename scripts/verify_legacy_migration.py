"""Assertions used by CI after migrating a populated v2 schema to v3."""
from __future__ import annotations

import os

from sqlalchemy import create_engine, text


def main() -> None:
    url = os.environ["ROBIA_DATABASE_URL"]
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            employee = connection.execute(
                text("SELECT cpf, cpf_last2, public_id, version FROM employees WHERE id=1")
            ).one()
            payment = connection.execute(
                text("SELECT public_id, currency, version, updated_at FROM payments WHERE id=1")
            ).one()
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert revision == "0002"
        assert employee.cpf != "52998224725"
        assert len(employee.cpf) == 64
        assert employee.cpf_last2 == "25"
        assert employee.public_id
        assert employee.version == 1
        assert payment.public_id
        assert payment.currency == "BRL"
        assert payment.version == 1
        assert payment.updated_at is not None
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
