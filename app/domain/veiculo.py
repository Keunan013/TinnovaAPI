from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Optional


@dataclass
class Veiculo:
    id: Optional[int]
    placa: str
    marca: str
    modelo: str
    ano: int
    cor: str
    preco_usd: Decimal
    ativo: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
