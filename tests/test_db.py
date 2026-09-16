from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from robia_ops.config import Settings
from robia_ops.db import build_engine


def test_sqlite_engine_configures_runtime_directory_and_pragmas(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "robia.db"
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{db_path}",
        sqlite_busy_timeout_ms=1234,
    )
    engine = build_engine(settings)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
            assert connection.execute(text("PRAGMA busy_timeout")).scalar_one() == 1234
        assert db_path.parent.exists()
    finally:
        engine.dispose()
