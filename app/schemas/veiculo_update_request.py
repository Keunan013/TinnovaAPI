from decimal import Decimal
from pydantic import BaseModel, Field


class VeiculoUpdateRequest(BaseModel):
    marca: str = Field(min_length=1, max_length=100)
    modelo: str = Field(min_length=1, max_length=100)
    ano: int = Field(ge=1886, le=2100)
    cor: str = Field(min_length=1, max_length=50)
    preco_brl: Decimal = Field(gt=0)
