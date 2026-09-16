from decimal import Decimal

from robia_ops.integrations import ProviderRequest, SandboxPaymentProvider


def test_sandbox_provider_is_deterministic_and_local() -> None:
    provider = SandboxPaymentProvider()
    request = ProviderRequest(1, "employee:1", Decimal("1000"), Decimal("200"))
    first = provider.process(request, dry_run=False)
    second = provider.process(request, dry_run=False)
    assert first.ok
    assert first.retryable is False
    assert first.reference == second.reference
    assert first.reference.startswith("sbx_")
    assert "no real transfer" in first.message.lower()


def test_dry_run_is_explicit() -> None:
    provider = SandboxPaymentProvider()
    result = provider.process(ProviderRequest(2, "employee:2", Decimal("1"), Decimal("0")), dry_run=True)
    assert result.ok
    assert "no transfer" in result.message.lower()


def test_sandbox_reference_is_bound_to_provider_idempotency_key() -> None:
    provider = SandboxPaymentProvider()
    common = dict(
        payment_id=7,
        employee_reference="employee:public",
        salary=Decimal("1000"),
        meal_allowance=Decimal("200"),
    )
    first = provider.process(ProviderRequest(**common, idempotency_key="payment:a"), dry_run=False)
    same = provider.process(ProviderRequest(**common, idempotency_key="payment:a"), dry_run=False)
    other = provider.process(ProviderRequest(**common, idempotency_key="payment:b"), dry_run=False)
    assert first.reference == same.reference
    assert first.reference != other.reference
