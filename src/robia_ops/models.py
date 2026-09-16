from __future__ import annotations

import enum
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_public_id() -> str:
    return str(uuid4())


class PaymentStatus(str, enum.Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    PROCESSED = "processed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PayrollRunStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint("salary > 0", name="ck_employees_salary_positive"),
        CheckConstraint("meal_allowance >= 0", name="ck_employees_meal_allowance_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, default=new_public_id)
    name: Mapped[str] = mapped_column(String(120), index=True)
    # The historical database column remains named ``cpf`` for migration compatibility,
    # but v3 stores only a keyed HMAC fingerprint, never the raw CPF.
    cpf_fingerprint: Mapped[str] = mapped_column("cpf", String(64), unique=True, index=True)
    cpf_last2: Mapped[str] = mapped_column(String(2))
    salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    meal_allowance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    active: Mapped[bool] = mapped_column(default=True, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    payments: Mapped[list["Payment"]] = relationship(back_populates="employee", cascade="all, delete-orphan")

    __mapper_args__ = {"version_id_col": version}


class PayrollRun(Base):
    __tablename__ = "payroll_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, default=new_public_id)
    reference_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    status: Mapped[PayrollRunStatus] = mapped_column(
        Enum(PayrollRunStatus), default=PayrollRunStatus.RUNNING, index=True
    )
    employees_total: Mapped[int] = mapped_column(Integer, default=0)
    payments_created: Mapped[int] = mapped_column(Integer, default=0)
    payments_existing: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    payments: Mapped[list["Payment"]] = relationship(back_populates="payroll_run")


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_employee_period", "employee_id", "reference_date"),
        CheckConstraint("salary > 0", name="ck_payments_salary_positive"),
        CheckConstraint("meal_allowance >= 0", name="ck_payments_meal_allowance_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, default=new_public_id)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    payroll_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("payroll_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    meal_allowance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(3), default="BRL")
    reference_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.DRAFT, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), unique=True, nullable=True)
    request_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    employee: Mapped[Employee] = relationship(back_populates="payments")
    payroll_run: Mapped[PayrollRun | None] = relationship(back_populates="payments")
    attempts: Mapped[list["PaymentAttempt"]] = relationship(
        back_populates="payment", cascade="all, delete-orphan", order_by="PaymentAttempt.id"
    )

    __mapper_args__ = {"version_id_col": version}

    @property
    def total(self) -> Decimal:
        return self.salary + self.meal_allowance


class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"
    __table_args__ = (
        Index("ix_payment_attempts_payment_attempt", "payment_id", "attempt_number", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), index=True)
    attempt_number: Mapped[int] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(String(80), index=True)
    dry_run: Mapped[bool] = mapped_column(default=False)
    success: Mapped[bool | None] = mapped_column(nullable=True)
    retryable: Mapped[bool] = mapped_column(default=False)
    provider_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    payment: Mapped[Payment] = relationship(back_populates="attempts")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    entity_id: Mapped[str] = mapped_column(String(80), index=True)
    actor: Mapped[str] = mapped_column(String(120), default="system")
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, default=new_public_id)
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    aggregate_type: Mapped[str] = mapped_column(String(80), index=True)
    aggregate_id: Mapped[str] = mapped_column(String(80), index=True)
    payload: Mapped[str] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
