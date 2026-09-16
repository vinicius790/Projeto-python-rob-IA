from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from robia_ops.api.dependencies import get_settings
from robia_ops.config import Settings
from robia_ops.db import Base, get_db
from robia_ops.main import create_app


def _secured_client(settings: Settings):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    app = create_app(settings)

    def override_db() -> Generator[Session, None, None]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    return engine, TestClient(app, raise_server_exceptions=False)


def test_legacy_api_key_is_admin_compatible() -> None:
    settings = Settings(
        _env_file=None,
        env="test",
        api_key="secret-test-key",
        pii_key="test-pii",
        allowed_hosts="testserver",
    )
    engine, client = _secured_client(settings)
    payload = {"name": "Protected", "cpf": "52998224725", "salary": "4000", "meal_allowance": "500"}
    try:
        with client:
            assert client.get("/api/v1/employees").status_code == 401
            assert client.post("/api/v1/employees", json=payload).status_code == 401
            assert client.post("/api/v1/employees", json=payload, headers={"X-API-Key": "wrong"}).status_code == 401
            headers = {"X-API-Key": "secret-test-key"}
            assert client.post("/api/v1/employees", json=payload, headers=headers).status_code == 201
            assert client.get("/api/v1/audit", headers=headers).status_code == 200
    finally:
        engine.dispose()


def test_scoped_keys_enforce_read_write_admin_boundaries() -> None:
    settings = Settings(
        _env_file=None,
        env="test",
        read_api_key="read-key",
        write_api_key="write-key",
        admin_api_key="admin-key",
        pii_key="test-pii",
        allowed_hosts="testserver",
    )
    engine, client = _secured_client(settings)
    payload = {"name": "Scoped", "cpf": "52998224725", "salary": "4000", "meal_allowance": "500"}
    try:
        with client:
            read = {"X-API-Key": "read-key"}
            write = {"X-API-Key": "write-key"}
            admin = {"X-API-Key": "admin-key"}
            assert client.get("/api/v1/employees", headers=read).status_code == 200
            assert client.post("/api/v1/employees", json=payload, headers=read).status_code == 403
            assert client.post("/api/v1/employees", json=payload, headers=write).status_code == 201
            assert client.get("/api/v1/employees", headers=write).status_code == 200
            assert client.get("/api/v1/audit", headers=write).status_code == 403
            assert client.get("/api/v1/audit", headers=admin).status_code == 200
    finally:
        engine.dispose()
