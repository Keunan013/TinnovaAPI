from sqlalchemy import Column, Integer, String, Boolean, Numeric, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class VeiculoModel(Base):
    __tablename__ = 'veiculos'
    id = Column(Integer, primary_key=True, index=True)
    placa = Column(String, unique=True, nullable=False, index=True)
    marca = Column(String, nullable=False, index=True)
    modelo = Column(String, nullable=False)
    ano = Column(Integer, nullable=False, index=True)
    cor = Column(String, nullable=False)
    preco_usd = Column(Numeric(10, 2), nullable=False)
    ativo = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
