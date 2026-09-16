import pytest

from robia_ops.security.cpf import is_valid_cpf, mask_cpf, normalize_cpf


@pytest.mark.parametrize("value", ["529.982.247-25", "52998224725", "111.444.777-35"])
def test_valid_cpf(value: str) -> None:
    assert is_valid_cpf(value)


@pytest.mark.parametrize("value", ["", "11111111111", "123", "52998224724"])
def test_invalid_cpf(value: str) -> None:
    assert not is_valid_cpf(value)


def test_normalize_and_mask() -> None:
    assert normalize_cpf("529.982.247-25") == "52998224725"
    assert mask_cpf("52998224725") == "***.***.***-25"
    assert mask_cpf("bad") == "***"
