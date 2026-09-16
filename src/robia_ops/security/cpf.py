from __future__ import annotations

import re

_NON_DIGITS = re.compile(r"\D+")


def normalize_cpf(value: str) -> str:
    return _NON_DIGITS.sub("", value or "")


def is_valid_cpf(value: str) -> bool:
    cpf = normalize_cpf(value)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for index in (9, 10):
        total = sum(int(cpf[i]) * ((index + 1) - i) for i in range(index))
        digit = (total * 10) % 11
        if digit == 10:
            digit = 0
        if digit != int(cpf[index]):
            return False
    return True


def mask_cpf(value: str) -> str:
    cpf = normalize_cpf(value)
    if len(cpf) != 11:
        return "***"
    return f"***.***.***-{cpf[-2:]}"
