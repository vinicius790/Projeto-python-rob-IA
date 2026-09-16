from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ...schemas import AnalyticsSummary, AnomalyResult, MonthlyPayrollPoint
from ...services.analytics import detect_anomalies, monthly_payroll, summary
from ..dependencies import AppSettings, DBSession, require_read

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(require_read)])


@router.get("/summary", response_model=AnalyticsSummary)
def analytics_summary(db: DBSession) -> AnalyticsSummary:
    return summary(db)


@router.get("/monthly-payroll", response_model=list[MonthlyPayrollPoint])
def monthly_payroll_route(
    db: DBSession,
    months: int = Query(default=12, ge=1, le=60),
) -> list[MonthlyPayrollPoint]:
    return monthly_payroll(db, months=months)


@router.get("/payment-anomalies", response_model=list[AnomalyResult])
def payment_anomalies(db: DBSession, settings: AppSettings) -> list[AnomalyResult]:
    return detect_anomalies(db, contamination=settings.anomaly_contamination)
