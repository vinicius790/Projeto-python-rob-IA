from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient


def employee_json() -> dict:
    return {
        "name": "Ana API",
        "cpf": "52998224725",
        "salary": "4200.00",
        "meal_allowance": "650.00",
    }


def test_health_liveness_meta_and_security_headers(client: TestClient) -> None:
    live = client.get("/api/v1/live")
    assert live.status_code == 200
    assert live.json()["status"] == "alive"

    response = client.get("/api/v1/health", headers={"X-Request-ID": "known-request"})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["x-request-id"] == "known-request"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "no-store"

    meta = client.get("/api/v1/meta")
    assert meta.status_code == 200
    assert meta.json()["version"] == "3.0.0"
    assert meta.json()["provider"] == "sandbox"


def test_employee_api_masks_cpf_and_exposes_public_id(client: TestClient) -> None:
    created = client.post("/api/v1/employees", json=employee_json())
    assert created.status_code == 201
    body = created.json()
    assert body["cpf"] == "***.***.***-25"
    assert body["public_id"]

    listed = client.get("/api/v1/employees")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert "52998224725" not in listed.text


def test_employee_validation(client: TestClient) -> None:
    payload = employee_json() | {"cpf": "11111111111"}
    response = client.post("/api/v1/employees", json=payload)
    assert response.status_code == 422


def test_payment_flow_idempotency_attempts_and_outbox(client: TestClient) -> None:
    employee_id = client.post("/api/v1/employees", json=employee_json()).json()["id"]
    payload = {"employee_id": employee_id, "reference_date": date.today().isoformat()}
    headers = {"Idempotency-Key": "api-payment-1"}
    first = client.post("/api/v1/payments", json=payload, headers=headers)
    second = client.post("/api/v1/payments", json=payload, headers=headers)
    assert first.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    mismatch = client.post(
        "/api/v1/payments",
        json=payload | {"reference_date": "2026-12-01"},
        headers=headers,
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "conflict"

    payment_id = first.json()["id"]
    dry_run = client.post(f"/api/v1/payments/{payment_id}/process", json={"dry_run": True})
    assert dry_run.status_code == 200
    assert dry_run.json()["payment"]["status"] == "draft"
    assert dry_run.json()["attempts"] == 1

    processed = client.post(f"/api/v1/payments/{payment_id}/process", json={"dry_run": False})
    assert processed.status_code == 200
    assert processed.json()["payment"]["status"] == "processed"
    assert processed.json()["attempts"] == 1

    attempts = client.get(f"/api/v1/payments/{payment_id}/attempts")
    assert attempts.status_code == 200
    assert len(attempts.json()) == 2

    outbox = client.get("/api/v1/operations/outbox")
    assert outbox.status_code == 200
    assert any(item["event_type"] == "payment.processed" for item in outbox.json())


def test_dashboard(client: TestClient) -> None:
    client.post("/api/v1/employees", json=employee_json())
    response = client.get("/")
    assert response.status_code == 200
    assert "RobIA Ops" in response.text
    assert "sandbox" in response.text.lower()
    assert "52998224725" not in response.text


def test_analytics_audit_monthly_and_metrics(client: TestClient) -> None:
    employee = client.post("/api/v1/employees", json=employee_json()).json()
    client.post(
        "/api/v1/payments",
        json={"employee_id": employee["id"], "reference_date": "2026-09-01"},
    )
    summary = client.get("/api/v1/analytics/summary")
    assert summary.status_code == 200
    assert summary.json()["employees_total"] == 1
    assert summary.json()["failed_total"] == 0

    monthly = client.get("/api/v1/analytics/monthly-payroll")
    assert monthly.status_code == 200
    assert monthly.json()[0]["month"] == "2026-09"

    audit = client.get("/api/v1/audit")
    assert audit.status_code == 200
    assert audit.json()[0]["action"] == "payment.created"
    assert audit.json()[0]["request_id"]

    metrics = client.get("/api/v1/metrics")
    assert metrics.status_code == 200
    assert "robia_http_requests_total" in metrics.text


def test_payroll_run_endpoints_are_idempotent(client: TestClient) -> None:
    client.post("/api/v1/employees", json=employee_json())
    payload = {"reference_date": "2026-09-01"}
    first = client.post("/api/v1/payroll-runs", json=payload)
    second = client.post("/api/v1/payroll-runs", json=payload)
    assert first.status_code == 201
    assert first.json()["created"] == 1
    assert second.json()["created"] == 0
    assert second.json()["existing"] == 1
    assert second.json()["payroll_run_id"] == first.json()["payroll_run_id"]

    listed = client.get("/api/v1/payroll-runs")
    assert listed.status_code == 200 and listed.json()["total"] == 1
    fetched = client.get(f"/api/v1/payroll-runs/{first.json()['payroll_run_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "completed"


def test_legacy_generate_payroll_endpoint_kept_for_compatibility(client: TestClient) -> None:
    client.post("/api/v1/employees", json=employee_json())
    payload = {"reference_date": "2026-10-01"}
    first = client.post("/api/v1/payments/generate-payroll", json=payload)
    second = client.post("/api/v1/payments/generate-payroll", json=payload)
    assert first.status_code == 200
    assert first.json()["created"] == 1
    assert first.json()["payroll_run_public_id"]
    assert second.json()["created"] == 0
    assert second.json()["existing"] == 1


def test_production_root_does_not_render_dashboard(session_factory) -> None:
    from robia_ops.api.dependencies import get_settings
    from robia_ops.config import Settings
    from robia_ops.db import get_db
    from robia_ops.main import create_app

    settings = Settings(
        _env_file=None,
        env="production",
        api_key="prod-key",
        pii_key="prod-pii-key",
        allowed_hosts="testserver",
    )
    app = create_app(settings)

    def override_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app, raise_server_exceptions=False) as local_client:
        response = local_client.get("/")
        docs = local_client.get("/docs")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert docs.status_code == 404
    assert response.headers["strict-transport-security"].startswith("max-age=")


def test_employee_update_get_deactivate_and_payment_cancel(client: TestClient) -> None:
    employee = client.post("/api/v1/employees", json=employee_json()).json()
    fetched = client.get(f"/api/v1/employees/{employee['id']}")
    assert fetched.status_code == 200
    updated = client.patch(f"/api/v1/employees/{employee['id']}", json={"salary": "4500.00"})
    assert updated.status_code == 200 and updated.json()["salary"] == "4500.00"

    payment = client.post(
        "/api/v1/payments",
        json={"employee_id": employee["id"], "reference_date": "2026-11-01"},
    ).json()
    fetched_payment = client.get(f"/api/v1/payments/{payment['id']}")
    assert fetched_payment.status_code == 200
    cancelled = client.post(f"/api/v1/payments/{payment['id']}/cancel")
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"

    deactivated = client.delete(f"/api/v1/employees/{employee['id']}")
    assert deactivated.status_code == 200 and deactivated.json()["active"] is False


def test_audit_filters_and_outbox_ack(client: TestClient) -> None:
    employee = client.post("/api/v1/employees", json=employee_json()).json()
    payment = client.post(
        "/api/v1/payments",
        json={"employee_id": employee["id"], "reference_date": "2026-12-01"},
    ).json()
    client.post(f"/api/v1/payments/{payment['id']}/cancel")
    filtered = client.get("/api/v1/audit", params={"action": "payment.cancelled", "entity_type": "payment"})
    assert filtered.status_code == 200 and len(filtered.json()) == 1
    events = client.get("/api/v1/operations/outbox").json()
    event_id = events[0]["id"]
    ack = client.post(f"/api/v1/operations/outbox/{event_id}/ack")
    assert ack.status_code == 200 and ack.json()["published_at"] is not None


def test_missing_resources_use_structured_error(client: TestClient) -> None:
    response = client.get("/api/v1/employees/999")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"
    assert body["error"]["request_id"]


def test_metrics_can_be_disabled(session_factory) -> None:
    from robia_ops.api.dependencies import get_settings
    from robia_ops.config import Settings
    from robia_ops.db import get_db
    from robia_ops.main import create_app

    settings = Settings(_env_file=None, env="test", pii_key="test", allowed_hosts="testserver", enable_metrics=False)
    app = create_app(settings)

    def override_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app, raise_server_exceptions=False) as local_client:
        response = local_client.get("/api/v1/metrics")
    assert response.status_code == 404
