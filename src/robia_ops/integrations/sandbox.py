from __future__ import annotations

import hashlib

from .base import ProviderRequest, ProviderResult


class SandboxPaymentProvider:
    """Deterministic local provider used for development, tests and portfolio demos.

    It never sends money and never performs network requests.
    """

    name = "sandbox"

    def process(self, request: ProviderRequest, *, dry_run: bool = True) -> ProviderResult:
        token = (
            f"{request.payment_id}:{request.employee_reference}:{request.salary}:"
            f"{request.meal_allowance}:{request.currency}:{request.idempotency_key or ""}"
        )
        reference = "sbx_" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:20]
        if dry_run:
            return ProviderResult(True, reference, "Sandbox validation completed; no transfer executed.")
        return ProviderResult(True, reference, "Sandbox payment marked as processed; no real transfer occurred.")
