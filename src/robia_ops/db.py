from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import Settings, get_settings


class Base(DeclarativeBase):
    pass


def _configure_sqlite(
    dbapi_connection,
    _connection_record,
    *,
    busy_timeout_ms: int,
) -> None:  # type: ignore[no-untyped-def]
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute(f"PRAGMA busy_timeout={int(busy_timeout_ms)}")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def build_engine(settings: Settings) -> Engine:
    settings.ensure_runtime_dirs()
    if settings.database_url.startswith("sqlite"):
        engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            connect_args={"check_same_thread": False},
        )
        event.listen(
            engine,
            "connect",
            lambda connection, record: _configure_sqlite(  # noqa: ARG005
                connection, record, busy_timeout_ms=settings.sqlite_busy_timeout_ms
            ),
        )
        return engine

    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle_seconds,
    )


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return build_engine(get_settings())


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(engine: Engine | None = None) -> None:
    from . import models  # noqa: F401

    Base.metadata.create_all(engine or get_engine())


def clear_database_caches() -> None:
    # Dispose an existing cached engine before dropping the cache. This matters
    # for SQLite because otherwise open DB-API connections can survive until
    # garbage collection and emit ResourceWarning during test/CLI reconfiguration.
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_session_factory.cache_clear()
    get_engine.cache_clear()
