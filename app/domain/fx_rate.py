from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class FxRate:
    usd_brl: Decimal
