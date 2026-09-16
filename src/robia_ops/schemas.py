from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import PaymentStatus, PayrollRunStatus
from .security.cpf import is_valid_cpf, normalize_cpf
from .security.pii import mask_from_last2


class EmployeeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    cpf: str
    salary: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    meal_allowance: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Nome deve conter ao menos 2 caracteres úteis")
        return cleaned

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, value: str) -> str:
        normalized = normalize_cpf(value)
        if not is_valid_cpf(normalized):
            raise ValueError("CPF inválido")
        return normalized


class EmployeeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    salary: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    meal_allowance: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    active: bool | None = None

    @field_validator("name")
    @classmethod
    def clean_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Nome deve conter ao menos 2 caracteres úteis")
        return cleaned


class EmployeeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: str
    name: str
    cpf: str
    salary: Decimal
    meal_allowance: Decimal
    active: bool
    version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, employee) -> "EmployeeRead":  # type: ignore[no-untyped-def]
        return cls(
            id=employee.id,
            public_id=employee.public_id,
            name=employee.name,
            cpf=mask_from_last2(employee.cpf_last2),
            salary=employee.salary,
            meal_allowance=employee.meal_allowance,
            active=employee.active,
            version=employee.version,
            created_at=employee.created_at,
            updated_at=employee.updated_at,
        )


class PaymentCreate(BaseModel):
    employee_id: int = Field(gt=0)
    reference_date: date
    salary: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    meal_allowance: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.upper()
        if not value.isalpha():
            raise ValueError("currency must contain only letters")
        return value


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: str
    employee_id: int
    payroll_run_id: int | None
    salary: Decimal
    meal_allowance: Decimal
    currency: str
    reference_date: date
    status: PaymentStatus
    idempotency_key: str | None
    provider_reference: str | None
    failure_reason: str | None
    version: int
    created_at: datetime
    updated_at: datetime
    processed_at: datetime | None

    @property
    def total(self) -> Decimal:
        return self.salary + self.meal_allowance


class PaymentAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    payment_id: int
    attempt_number: int
    provider: str
    dry_run: bool
    success: bool | None
    retryable: bool
    provider_reference: str | None
    message: str | None
    started_at: datetime
    finished_at: datetime | None


class PayrollGenerateRequest(BaseModel):
    reference_date: date


class PayrollGenerateResult(BaseModel):
    reference_date: date
    payroll_run_id: int
    payroll_run_public_id: str
    created: int
    existing: int
    payment_ids: list[int]


class PayrollRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: str
    reference_date: date
    status: PayrollRunStatus
    employees_total: int
    payments_created: int
    payments_existing: int
    created_at: datetime
    completed_at: datetime | None


class PaymentProcessRequest(BaseModel):
    dry_run: bool = True


class PaymentProcessResult(BaseModel):
    payment: PaymentRead
    provider: str
    dry_run: bool
    message: str
    attempts: int


class AnalyticsSummary(BaseModel):
    employees_total: int
    employees_active: int
    payments_total: int
    processed_total: int
    failed_total: int
    payroll_total: Decimal
    average_payment: Decimal


class MonthlyPayrollPoint(BaseModel):
    month: str
    payments: int
    total: Decimal


class AnomalyResult(BaseModel):
    payment_id: int
    score: float
    is_anomaly: bool
    model: str
    reasons: list[str]


class PaginatedEmployees(BaseModel):
    items: list[EmployeeRead]
    total: int
    limit: int
    offset: int


class PaginatedPayments(BaseModel):
    items: list[PaymentRead]
    total: int
    limit: int
    offset: int


class PaginatedPayrollRuns(BaseModel):
    items: list[PayrollRunRead]
    total: int
    limit: int
    offset: int


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str


class MetaResponse(BaseModel):
    service: str
    version: str
    environment: str
    auth_enabled: bool
    provider: str
    dashboard_enabled: bool
    docs_enabled: bool
    metrics_enabled: bool


class OutboxEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    attempts: int
    created_at: datetime
    published_at: datetime | None


class ErrorMeta(BaseModel):
    code: str
    request_id: str | None = None


class ErrorResponse(BaseModel):
    detail: str
    error: ErrorMeta
