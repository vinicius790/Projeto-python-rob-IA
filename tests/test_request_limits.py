from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from robia_ops.api.dependencies import get_settings
from robia_ops.config import Settings
from robia_ops.db import get_db
from robia_ops.main import create_app


def test_request_body_limit(session_factory) -> None:
    settings = Settings(
        _env_file=None,
        env="test",
        pii_key="test-key",
        allowed_hosts="testserver",
        max_request_bytes=1024,
    )
    app = create_app(settings)

    def override_db() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    huge = {
        "name": "A" * 2000,
        "cpf": "52998224725",
        "salary": "1000",
        "meal_allowance": "0",
    }
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/v1/employees", json=huge)
    assert response.status_code == 413
