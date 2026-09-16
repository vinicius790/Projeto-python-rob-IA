from __future__ import annotations

import hmac
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..integrations import SandboxPaymentProvider
from ..security.auth import AccessScope, Principal

DBSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def _candidate_keys(settings: Settings) -> list[tuple[str, str, AccessScope]]:
    candidates: list[tuple[str, str, AccessScope]] = []
    if settings.read_api_key:
        candidates.append(("read-key", settings.read_api_key.get_secret_value(), AccessScope.READ))
    if settings.write_api_key:
        candidates.append(("write-key", settings.write_api_key.get_secret_value(), AccessScope.WRITE))
    if settings.admin_api_key:
        candidates.append(("admin-key", settings.admin_api_key.get_secret_value(), AccessScope.ADMIN))
    if settings.api_key:
        candidates.append(("legacy-admin-key", settings.api_key.get_secret_value(), AccessScope.ADMIN))
    return candidates


def authorize(required: AccessScope) -> Callable[..., Principal]:
    def dependency(
        settings: AppSettings,
        x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    ) -> Principal:
        candidates = _candidate_keys(settings)
        if not candidates:
            return Principal(name="development-anonymous", scope=AccessScope.ADMIN, authenticated=False)
        if not x_api_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key ausente")
        for name, expected, scope in candidates:
            if hmac.compare_digest(x_api_key, expected):
                principal = Principal(name=name, scope=scope, authenticated=True)
                if not principal.allows(required):
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Escopo insuficiente")
                return principal
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key inválida")

    return dependency


require_read = authorize(AccessScope.READ)
require_write = authorize(AccessScope.WRITE)
require_admin = authorize(AccessScope.ADMIN)
# Backward-compatible alias: old callers expected the single configured key to protect all routes.
require_api_key = require_read


def get_provider(settings: AppSettings) -> SandboxPaymentProvider:
    # Only sandbox is intentionally supported until a real provider contract is verified.
    return SandboxPaymentProvider()
