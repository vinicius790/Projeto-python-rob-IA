from robia_ops.security.pii import cpf_last2, fingerprint_cpf, mask_from_last2


def test_cpf_fingerprint_is_keyed_and_deterministic() -> None:
    first = fingerprint_cpf("529.982.247-25", "key-a")
    second = fingerprint_cpf("52998224725", "key-a")
    other_key = fingerprint_cpf("52998224725", "key-b")
    assert first == second
    assert first != other_key
    assert "52998224725" not in first
    assert cpf_last2("52998224725") == "25"
    assert mask_from_last2("25") == "***.***.***-25"
