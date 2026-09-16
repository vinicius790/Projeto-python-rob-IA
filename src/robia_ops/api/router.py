from fastapi import APIRouter

from .routes import analytics, audit, employees, health, metrics, operations, payments, payrolls

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(employees.router)
api_router.include_router(payments.router)
api_router.include_router(payrolls.router)
api_router.include_router(analytics.router)
api_router.include_router(audit.router)
api_router.include_router(operations.router)
api_router.include_router(metrics.router)
