from app.domain.veiculo import Veiculo
from app.models.veiculo_model import VeiculoModel
from app.schemas.veiculo_response import VeiculoResponse


def to_domain(model: VeiculoModel) -> Veiculo:
    return Veiculo(
        id=model.id,
        placa=model.placa,
        marca=model.marca,
        modelo=model.modelo,
        ano=model.ano,
        cor=model.cor,
        preco_usd=model.preco_usd,
        ativo=model.ativo,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def to_model(domain: Veiculo) -> VeiculoModel:
    return VeiculoModel(
        id=domain.id,
        placa=domain.placa,
        marca=domain.marca,
        modelo=domain.modelo,
        ano=domain.ano,
        cor=domain.cor,
        preco_usd=domain.preco_usd,
        ativo=domain.ativo,
    )

def to_dto(domain: Veiculo) -> VeiculoResponse:
    return VeiculoResponse(
        id=domain.id,
        placa=domain.placa,
        marca=domain.marca,
        modelo=domain.modelo,
        ano=domain.ano,
        cor=domain.cor,
        preco_usd=domain.preco_usd,
        ativo=domain.ativo,
    )
