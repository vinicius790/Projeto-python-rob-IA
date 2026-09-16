from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class AccessScope(IntEnum):
    READ = 10
    WRITE = 20
    ADMIN = 30


@dataclass(frozen=True, slots=True)
class Principal:
    name: str
    scope: AccessScope
    authenticated: bool

    def allows(self, required: AccessScope) -> bool:
        return self.scope >= required
