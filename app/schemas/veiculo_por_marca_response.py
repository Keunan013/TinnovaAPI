from pydantic import BaseModel


class VeiculoPorMarcaResponse(BaseModel):
    marca: str
    quantidade: int
