from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedEmail:
    value: str
    domain: str
