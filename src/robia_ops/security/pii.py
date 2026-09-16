from __future__ import annotations

import hashlib
import hmac

from .cpf import normalize_cpf


def fingerprint_cpf(cpf: str, secret: str) -> str:
    """Return a keyed, non-reversible fingerprint for a normalized CPF.

    A plain hash is intentionally avoided because the CPF input space is small
    enough to be enumerated offline.  The HMAC key must be supplied through the
    application configuration and must be changed for production deployments.
    """

    normalized = normalize_cpf(cpf)
    return hmac.new(secret.encode("utf-8"), normalized.encode("ascii"), hashlib.sha256).hexdigest()


def cpf_last2(cpf: str) -> str:
    normalized = normalize_cpf(cpf)
    return normalized[-2:]


def mask_from_last2(last2: str) -> str:
    return f"***.***.***-{last2}"
