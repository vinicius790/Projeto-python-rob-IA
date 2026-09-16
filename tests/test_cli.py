from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from robia_ops.cli import app
from robia_ops.config import clear_settings_cache
from robia_ops.db import clear_database_caches

runner = CliRunner()


def _reset() -> None:
    clear_settings_cache()
    clear_database_caches()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "3.0.0" in result.stdout


def test_security_check_does_not_print_secret(monkeypatch) -> None:
    monkeypatch.setenv("ROBIA_API_KEY", "top-secret")
    monkeypatch.setenv("ROBIA_PII_KEY", "pii-secret")
    _reset()
    result = runner.invoke(app, ["security-check"])
    _reset()
    assert result.exit_code == 0
    assert "top-secret" not in result.stdout
    assert "pii-secret" not in result.stdout
    assert "Payment provider" in result.stdout


def test_operational_cli_flow(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "cli.db"
    export_path = tmp_path / "exports" / "payments.csv"
    monkeypatch.setenv("ROBIA_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("ROBIA_PII_KEY", "cli-test-pii")
    monkeypatch.setenv("ROBIA_PROVIDER_RETRY_BASE_SECONDS", "0")
    _reset()
    try:
        init = runner.invoke(app, ["init-db"])
        assert init.exit_code == 0 and "initialized" in init.stdout.lower()

        seed = runner.invoke(app, ["seed-demo"])
        assert seed.exit_code == 0 and "Seeded 3" in seed.stdout
        seeded_again = runner.invoke(app, ["seed-demo"])
        assert seeded_again.exit_code == 0 and "skipped" in seeded_again.stdout.lower()

        payroll = runner.invoke(app, ["generate-payroll", "2026-09-01", "--json"])
        assert payroll.exit_code == 0 and '"created": 3' in payroll.stdout
        invalid = runner.invoke(app, ["generate-payroll", "bad-date"])
        assert invalid.exit_code != 0

        processed = runner.invoke(app, ["process-payment", "1", "--commit"])
        assert processed.exit_code == 0 and "processed" in processed.stdout

        outbox = runner.invoke(app, ["outbox"])
        assert outbox.exit_code == 0 and "payment.processed" in outbox.stdout

        exported = runner.invoke(app, ["export-payments", str(export_path)])
        assert exported.exit_code == 0
        assert export_path.exists()
        assert "cpf" not in export_path.read_text(encoding="utf-8").lower()

        doctor = runner.invoke(app, ["doctor"])
        assert doctor.exit_code == 0 and "Database" in doctor.stdout
    finally:
        _reset()
