from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from ...schemas import EmployeeCreate, EmployeeRead, EmployeeUpdate, PaginatedEmployees
from ...services import employees as service
from ..dependencies import AppSettings, DBSession, require_read, require_write

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=PaginatedEmployees, dependencies=[Depends(require_read)])
def list_employees(
    db: DBSession,
    settings: AppSettings,
    search: str | None = Query(default=None, min_length=1, max_length=120),
    active: bool | None = None,
    limit: int = Query(default=50, ge=1),
    offset: int = Query(default=0, ge=0),
) -> PaginatedEmployees:
    limit = min(limit, settings.max_page_size)
    items, total = service.list_employees(db, search=search, active=active, limit=limit, offset=offset)
    return PaginatedEmployees(
        items=[EmployeeRead.from_model(item) for item in items], total=total, limit=limit, offset=offset
    )


@router.post(
    "",
    response_model=EmployeeRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write)],
)
def create_employee(payload: EmployeeCreate, db: DBSession, settings: AppSettings) -> EmployeeRead:
    return EmployeeRead.from_model(
        service.create_employee(db, payload, pii_key=settings.pii_key.get_secret_value())
    )


@router.get("/{employee_id}", response_model=EmployeeRead, dependencies=[Depends(require_read)])
def get_employee(employee_id: int, db: DBSession) -> EmployeeRead:
    return EmployeeRead.from_model(service.get_employee(db, employee_id))


@router.patch(
    "/{employee_id}",
    response_model=EmployeeRead,
    dependencies=[Depends(require_write)],
)
def update_employee(employee_id: int, payload: EmployeeUpdate, db: DBSession) -> EmployeeRead:
    return EmployeeRead.from_model(service.update_employee(db, employee_id, payload))


@router.delete(
    "/{employee_id}",
    response_model=EmployeeRead,
    dependencies=[Depends(require_write)],
)
def deactivate_employee(employee_id: int, db: DBSession) -> EmployeeRead:
    return EmployeeRead.from_model(service.deactivate_employee(db, employee_id))
