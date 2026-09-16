from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from statistics import mean, pstdev

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Employee, Payment, PaymentStatus
from ..schemas import AnalyticsSummary, AnomalyResult, MonthlyPayrollPoint


def summary(db: Session) -> AnalyticsSummary:
    employees_total = int(db.scalar(select(func.count()).select_from(Employee)) or 0)
    employees_active = int(
        db.scalar(select(func.count()).select_from(Employee).where(Employee.active.is_(True))) or 0
    )
    payments_total = int(db.scalar(select(func.count()).select_from(Payment)) or 0)
    processed_total = int(
        db.scalar(
            select(func.count()).select_from(Payment).where(Payment.status == PaymentStatus.PROCESSED)
        )
        or 0
    )
    failed_total = int(
        db.scalar(select(func.count()).select_from(Payment).where(Payment.status == PaymentStatus.FAILED))
        or 0
    )
    payroll_total_raw = db.scalar(select(func.sum(Payment.salary + Payment.meal_allowance)))
    payroll_total = Decimal(payroll_total_raw or Decimal("0.00"))
    average = payroll_total / payments_total if payments_total else Decimal("0.00")
    return AnalyticsSummary(
        employees_total=employees_total,
        employees_active=employees_active,
        payments_total=payments_total,
        processed_total=processed_total,
        failed_total=failed_total,
        payroll_total=payroll_total,
        average_payment=average,
    )


def monthly_payroll(db: Session, *, months: int = 12) -> list[MonthlyPayrollPoint]:
    payments = list(
        db.scalars(
            select(Payment)
            .where(Payment.status != PaymentStatus.CANCELLED)
            .order_by(Payment.reference_date.desc(), Payment.id.desc())
        )
    )
    grouped: dict[str, tuple[int, Decimal]] = defaultdict(lambda: (0, Decimal("0.00")))
    for payment in payments:
        key = payment.reference_date.strftime("%Y-%m")
        count, total = grouped[key]
        grouped[key] = (count + 1, total + Decimal(payment.salary) + Decimal(payment.meal_allowance))
    keys = sorted(grouped, reverse=True)[:months]
    return [
        MonthlyPayrollPoint(month=key, payments=grouped[key][0], total=grouped[key][1])
        for key in reversed(keys)
    ]


def detect_anomalies(db: Session, *, contamination: float = 0.08) -> list[AnomalyResult]:
    payments = list(
        db.scalars(
            select(Payment)
            .where(Payment.status != PaymentStatus.CANCELLED)
            .order_by(Payment.id)
        )
    )
    if not payments:
        return []

    totals = [float(Decimal(p.salary) + Decimal(p.meal_allowance)) for p in payments]
    fallback_scores = _z_scores(totals)

    if len(payments) >= 8:
        try:
            from sklearn.ensemble import IsolationForest

            features = [
                [float(p.salary), float(p.meal_allowance), total]
                for p, total in zip(payments, totals, strict=True)
            ]
            model = IsolationForest(contamination=contamination, random_state=42)
            predictions = model.fit_predict(features)
            decision = model.decision_function(features)
            return [
                AnomalyResult(
                    payment_id=p.id,
                    score=float(-decision[i]),
                    is_anomaly=bool(predictions[i] == -1),
                    model="isolation_forest",
                    reasons=_reasons(totals[i], fallback_scores[i]),
                )
                for i, p in enumerate(payments)
            ]
        except ImportError:
            pass

    return [
        AnomalyResult(
            payment_id=p.id,
            score=abs(fallback_scores[i]),
            is_anomaly=abs(fallback_scores[i]) >= 2.5,
            model="statistical_fallback",
            reasons=_reasons(totals[i], fallback_scores[i]),
        )
        for i, p in enumerate(payments)
    ]


def _z_scores(values: list[float]) -> list[float]:
    if len(values) < 2:
        return [0.0] * len(values)
    spread = pstdev(values)
    if spread == 0:
        return [0.0] * len(values)
    center = mean(values)
    return [(value - center) / spread for value in values]


def _reasons(total: float, z_score: float) -> list[str]:
    reasons = []
    if abs(z_score) >= 2.5:
        reasons.append("Total de pagamento distante do padrão histórico")
    if total <= 0:
        reasons.append("Total não positivo")
    return reasons or ["Nenhum sinal estatístico forte no fallback explicável"]
