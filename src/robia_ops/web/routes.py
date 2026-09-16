from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..api.dependencies import DBSession
from ..services.analytics import summary
from ..services.employees import list_employees
from ..services.payments import list_payments

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
router = APIRouter(tags=["web"])


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard(request: Request, db: DBSession) -> HTMLResponse:
    employees, _ = list_employees(db, limit=8)
    payments, _ = list_payments(db, limit=8)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "summary": summary(db),
            "employees": employees,
            "payments": payments,
        },
    )
