from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class VeiculoResponse(BaseModel):
    id: int
    placa: str
    marca: str
    modelo: str
    ano: int
    cor: str
    ativo: bool
    preco_usd: Decimal
    preco_brl: Optional[Decimal] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
