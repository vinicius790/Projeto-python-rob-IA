"""Operational hardening, payroll runs, outbox and CPF data minimization.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-16

This migration intentionally replaces raw CPF values with keyed HMAC fingerprints.
That transformation is one-way, therefore downgrade is intentionally unsupported.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timezone
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

_DEV_PII_KEY = "robia-dev-pii-key-change-me"
payroll_run_status = sa.Enum("RUNNING", "COMPLETED", "FAILED", name="payrollrunstatus")


def _fingerprint(raw: str, secret: str) -> str:
    digits = "".join(ch for ch in raw if ch.isdigit())
    return hmac.new(secret.encode("utf-8"), digits.encode("ascii"), hashlib.sha256).hexdigest()


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(timezone.utc)

    op.add_column("employees", sa.Column("public_id", sa.String(length=36), nullable=True))
    op.add_column("employees", sa.Column("cpf_last2", sa.String(length=2), nullable=True))
    op.add_column("employees", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))

    secret = os.environ.get("ROBIA_PII_KEY", _DEV_PII_KEY)
    employee_rows = bind.execute(sa.text("SELECT id, cpf FROM employees")).fetchall()
    for employee_id, raw_cpf in employee_rows:
        raw_cpf = str(raw_cpf)
        digits = "".join(ch for ch in raw_cpf if ch.isdigit())
        bind.execute(
            sa.text(
                "UPDATE employees SET public_id=:public_id, cpf=:fingerprint, cpf_last2=:last2 "
                "WHERE id=:employee_id"
            ),
            {
                "public_id": str(uuid4()),
                "fingerprint": _fingerprint(raw_cpf, secret),
                "last2": digits[-2:],
                "employee_id": employee_id,
            },
        )

    with op.batch_alter_table("employees") as batch:
        batch.alter_column("public_id", nullable=False)
        batch.alter_column("cpf_last2", nullable=False)
        batch.alter_column("cpf", type_=sa.String(length=64), existing_nullable=False)
        batch.alter_column("version", server_default=None)
        batch.create_check_constraint("ck_employees_salary_positive", "salary > 0")
        batch.create_check_constraint(
            "ck_employees_meal_allowance_nonnegative", "meal_allowance >= 0"
        )
    op.create_index("ix_employees_public_id", "employees", ["public_id"], unique=True)

    op.create_table(
        "payroll_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("status", payroll_run_status, nullable=False),
        sa.Column("employees_total", sa.Integer(), nullable=False),
        sa.Column("payments_created", sa.Integer(), nullable=False),
        sa.Column("payments_existing", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("reference_date"),
    )
    op.create_index("ix_payroll_runs_public_id", "payroll_runs", ["public_id"], unique=True)
    op.create_index("ix_payroll_runs_reference_date", "payroll_runs", ["reference_date"], unique=True)
    op.create_index("ix_payroll_runs_status", "payroll_runs", ["status"])

    op.add_column("payments", sa.Column("public_id", sa.String(length=36), nullable=True))
    op.add_column("payments", sa.Column("payroll_run_id", sa.Integer(), nullable=True))
    op.add_column("payments", sa.Column("currency", sa.String(length=3), nullable=False, server_default="BRL"))
    op.add_column("payments", sa.Column("request_fingerprint", sa.String(length=64), nullable=True))
    op.add_column("payments", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("payments", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))

    payment_rows = bind.execute(sa.text("SELECT id, created_at FROM payments")).fetchall()
    for payment_id, created_at in payment_rows:
        bind.execute(
            sa.text("UPDATE payments SET public_id=:public_id, updated_at=:updated_at WHERE id=:payment_id"),
            {
                "public_id": str(uuid4()),
                "updated_at": created_at or now,
                "payment_id": payment_id,
            },
        )

    with op.batch_alter_table("payments") as batch:
        batch.alter_column("public_id", nullable=False)
        batch.alter_column("updated_at", nullable=False)
        batch.alter_column("idempotency_key", type_=sa.String(length=120), existing_nullable=True)
        batch.alter_column("currency", server_default=None)
        batch.alter_column("version", server_default=None)
        batch.create_foreign_key(
            "fk_payments_payroll_run_id",
            "payroll_runs",
            ["payroll_run_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_check_constraint("ck_payments_salary_positive", "salary > 0")
        batch.create_check_constraint(
            "ck_payments_meal_allowance_nonnegative", "meal_allowance >= 0"
        )
    op.create_index("ix_payments_public_id", "payments", ["public_id"], unique=True)
    op.create_index("ix_payments_payroll_run_id", "payments", ["payroll_run_id"])

    op.create_table(
        "payment_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_id", sa.Integer(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("retryable", sa.Boolean(), nullable=False),
        sa.Column("provider_reference", sa.String(length=120), nullable=True),
        sa.Column("message", sa.String(length=500), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_payment_attempts_payment_id", "payment_attempts", ["payment_id"])
    op.create_index("ix_payment_attempts_provider", "payment_attempts", ["provider"])
    op.create_index(
        "ix_payment_attempts_payment_attempt",
        "payment_attempts",
        ["payment_id", "attempt_number"],
        unique=True,
    )

    op.add_column("audit_events", sa.Column("request_id", sa.String(length=64), nullable=True))
    op.create_index("ix_audit_events_request_id", "audit_events", ["request_id"])

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("aggregate_type", sa.String(length=80), nullable=False),
        sa.Column("aggregate_id", sa.String(length=80), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_outbox_events_event_id", "outbox_events", ["event_id"], unique=True)
    op.create_index("ix_outbox_events_event_type", "outbox_events", ["event_type"])
    op.create_index("ix_outbox_events_aggregate_type", "outbox_events", ["aggregate_type"])
    op.create_index("ix_outbox_events_aggregate_id", "outbox_events", ["aggregate_id"])
    op.create_index("ix_outbox_events_created_at", "outbox_events", ["created_at"])
    op.create_index("ix_outbox_events_published_at", "outbox_events", ["published_at"])


def downgrade() -> None:
    raise RuntimeError(
        "Revision 0002 irreversibly replaces raw CPF values with keyed HMAC fingerprints; "
        "restore a pre-0002 database backup instead of downgrading."
    )
