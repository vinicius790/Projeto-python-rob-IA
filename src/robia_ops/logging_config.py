from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from .observability.context import get_request_id

_SENSITIVE_KEYS = {
    "cpf",
    "cpf_fingerprint",
    "api_key",
    "read_api_key",
    "write_api_key",
    "admin_api_key",
    "pii_key",
    "authorization",
    "token",
    "secret",
    "password",
}


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: "***" if k.lower() in _SENSITIVE_KEYS else _redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact(item) for item in value)
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = get_request_id()
        if request_id:
            payload["request_id"] = request_id
        extra = getattr(record, "context", None)
        if isinstance(extra, dict):
            payload["context"] = _redact(extra)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
