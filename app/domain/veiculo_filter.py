from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class VeiculoFilter:
    marca: Optional[str] = None
    ano: Optional[int] = None
    cor: Optional[str] = None
    min_preco_usd: Optional[Decimal] = None
    max_preco_usd: Optional[Decimal] = None
