from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Optional


class VeiculoPatchRequest(BaseModel):
    marca: Optional[str] = Field(default=None, min_length=1, max_length=100)
    modelo: Optional[str] = Field(default=None, min_length=1, max_length=100)
    ano: Optional[int] = Field(default=None, ge=1886, le=2100)
    cor: Optional[str] = Field(default=None, min_length=1, max_length=50)
    preco_brl: Optional[Decimal] = Field(default=None, gt=0)
