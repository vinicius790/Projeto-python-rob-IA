from __future__ import annotations

import csv
import json
import tempfile
from datetime import date
from pathlib import Path

import typer
import uvicorn
from rich.console import Console
from rich.table import Table
from sqlalchemy import select, text

from . import __version__
from .config import get_settings
from .db import get_engine, get_session_factory, init_db
from .integrations import SandboxPaymentProvider
from .models import Employee, Payment
from .schemas import EmployeeCreate, PaymentCreate
from .services.employees import create_employee
from .services.outbox import list_events, mark_published
from .services.payments import create_payment, process_payment
from .services.payrolls import generate_payroll_run

app = typer.Typer(help="RobIA Ops management CLI", no_args_is_help=True)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"robia {__version__}")
        raise typer.Exit()


@app.callback()
def root(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit.",
        is_eager=True,
        callback=_version_callback,
    ),
) -> None:
    """RobIA Ops operational and development commands."""


@app.command("init-db")
def init_database() -> None:
    """Create database tables for local/demo usage.

    Production deployments should prefer ``alembic upgrade head``.
    """
    init_db()
    console.print("[green]Database initialized.[/green]")


@app.command("seed-demo")
def seed_demo() -> None:
    """Insert deterministic synthetic data for local demonstrations."""
    settings = get_settings()
    init_db()
    session = get_session_factory()()
    try:
        if session.scalar(select(Employee.id).limit(1)):
            console.print("[yellow]Database already contains employees; seed skipped.[/yellow]")
            return
        employees = [
            EmployeeCreate(name="Ana Demo", cpf="52998224725", salary="4200.00", meal_allowance="650.00"),
            EmployeeCreate(name="Bruno Demo", cpf="11144477735", salary="5100.00", meal_allowance="700.00"),
            EmployeeCreate(name="Carla Demo", cpf="12345678909", salary="3900.00", meal_allowance="600.00"),
        ]
        created = [
            create_employee(session, item, pii_key=settings.pii_key.get_secret_value()) for item in employees
        ]
        for employee in created:
            create_payment(
                session,
                PaymentCreate(employee_id=employee.id, reference_date=date.today()),
                idempotency_key=f"demo-{employee.id}-{date.today().isoformat()}",
                default_currency=settings.default_currency,
            )
        console.print(f"[green]Seeded {len(created)} demo employees and payments.[/green]")
    finally:
        session.close()


@app.command("generate-payroll")
def generate_payroll_command(
    reference_date: str = typer.Argument(..., help="Reference date in YYYY-MM-DD format."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Create or reuse an idempotent payroll run for all active employees."""
    try:
        parsed_date = date.fromisoformat(reference_date)
    except ValueError as exc:
        raise typer.BadParameter("Use YYYY-MM-DD format") from exc
    settings = get_settings()
    init_db()
    session = get_session_factory()()
    try:
        run, payments, created, existing = generate_payroll_run(
            session, parsed_date, currency=settings.default_currency
        )
        payload = {
            "run_id": run.id,
            "run_public_id": run.public_id,
            "reference_date": run.reference_date.isoformat(),
            "payments": len(payments),
            "created": created,
            "existing": existing,
        }
        if json_output:
            console.print_json(json.dumps(payload))
        else:
            console.print(
                f"[green]Payroll run {run.public_id} ready:[/green] {len(payments)} payments "
                f"({created} created, {existing} already existed)."
            )
    finally:
        session.close()


@app.command("process-payment")
def process_payment_command(
    payment_id: int = typer.Argument(..., min=1),
    dry_run: bool = typer.Option(True, "--dry-run/--commit", help="Sandbox validation or state update."),
) -> None:
    """Process a payment through the configured provider (sandbox only in v3)."""
    settings = get_settings()
    session = get_session_factory()()
    try:
        payment, message = process_payment(
            session,
            payment_id,
            SandboxPaymentProvider(),
            dry_run=dry_run,
            max_attempts=settings.provider_max_attempts,
            retry_base_seconds=settings.provider_retry_base_seconds,
        )
        console.print(f"[green]{payment.status.value}[/green] payment #{payment.id}: {message}")
    finally:
        session.close()


@app.command("doctor")
def doctor() -> None:
    """Validate configuration, database connectivity and migration state."""
    settings = get_settings()
    checks = Table("Check", "Status", "Detail")
    checks.add_row("Environment", "OK", settings.env)
    try:
        with get_engine().connect() as connection:
            connection.exec_driver_sql("SELECT 1")
            try:
                revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
            except Exception:
                revision = None
        checks.add_row("Database", "OK", settings.database_url.split(":", 1)[0])
        checks.add_row("Alembic", "OK" if revision else "WARN", revision or "version table not found")
    except Exception as exc:  # pragma: no cover - environment-specific
        checks.add_row("Database", "FAIL", type(exc).__name__)
    checks.add_row("Provider", "OK", settings.provider)
    checks.add_row(
        "Auth",
        "OK" if settings.auth_enabled else "WARN",
        "enabled" if settings.auth_enabled else "disabled",
    )
    pii_default = settings.pii_key.get_secret_value() == "robia-dev-pii-key-change-me"
    checks.add_row("PII key", "WARN" if pii_default else "OK", "development default" if pii_default else "custom")
    console.print(checks)


@app.command("security-check")
def security_check() -> None:
    """Show deployment-security posture without printing secret values."""
    settings = get_settings()
    table = Table("Control", "Status", "Notes")
    table.add_row("Scoped API keys", "OK" if settings.auth_enabled else "WARN", "required in production")
    table.add_row(
        "PII fingerprint key",
        "WARN" if settings.pii_key.get_secret_value() == "robia-dev-pii-key-change-me" else "OK",
        "raw CPF is not persisted in v3",
    )
    table.add_row("Dashboard in production", "OK", "disabled by policy")
    table.add_row("Docs in production", "OK", "disabled by policy")
    table.add_row("Payment provider", "OK", "sandbox; no network transfer")
    console.print(table)


@app.command("outbox")
def outbox_command(
    all_events: bool = typer.Option(False, "--all", help="Include acknowledged events."),
    limit: int = typer.Option(100, min=1, max=500),
) -> None:
    """Inspect integration events waiting for an external publisher."""
    session = get_session_factory()()
    try:
        events, total = list_events(session, pending_only=not all_events, limit=limit)
        table = Table("ID", "Event", "Aggregate", "Published")
        for event in events:
            table.add_row(
                str(event.id),
                event.event_type,
                f"{event.aggregate_type}:{event.aggregate_id}",
                event.published_at.isoformat() if event.published_at else "pending",
            )
        console.print(table)
        console.print(f"{total} matching event(s)")
    finally:
        session.close()


@app.command("outbox-ack")
def outbox_ack(event_id: int = typer.Argument(..., min=1)) -> None:
    """Mark one outbox event as published after an external delivery succeeds."""
    session = get_session_factory()()
    try:
        event = mark_published(session, event_id)
        console.print(f"[green]Acknowledged outbox event {event.event_id}.[/green]")
    finally:
        session.close()


@app.command("export-payments")
def export_payments(path: Path = typer.Argument(Path("exports/payments.csv"))) -> None:
    """Export payment records atomically as CSV without CPF data."""
    path.parent.mkdir(parents=True, exist_ok=True)
    session = get_session_factory()()
    try:
        rows = list(session.scalars(select(Payment).order_by(Payment.id)))
        with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", delete=False, dir=path.parent) as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "public_id",
                    "employee_id",
                    "salary",
                    "meal_allowance",
                    "currency",
                    "reference_date",
                    "status",
                ]
            )
            for row in rows:
                writer.writerow(
                    [
                        row.public_id,
                        row.employee_id,
                        row.salary,
                        row.meal_allowance,
                        row.currency,
                        row.reference_date,
                        row.status.value,
                    ]
                )
            temp_path = Path(handle.name)
        temp_path.replace(path)
        console.print(f"[green]Exported {len(rows)} payments to {path}[/green]")
    finally:
        session.close()


@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8000, min=1, max=65535),
    reload: bool = typer.Option(False, help="Development auto-reload."),
) -> None:
    """Run the HTTP server."""
    uvicorn.run("robia_ops.main:app", host=host, port=port, reload=reload)
