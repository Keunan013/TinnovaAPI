from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.mappers.veiculo_mapper import to_dto
from app.schemas.common import Page
from app.schemas.veiculo_create_request import VeiculoCreateRequest
from app.schemas.veiculo_update_request import VeiculoUpdateRequest
from app.schemas.veiculo_patch_request import VeiculoPatchRequest
from app.schemas.veiculo_response import VeiculoResponse
from app.schemas.veiculo_por_marca_response import VeiculoPorMarcaResponse
from app.repositories.veiculo_repository import VeiculoRepository
from app.services.veiculo_service import VeiculoService
from app.services.fx.fx_provider import FxProvider
from app.services.fx.deps import get_fx_provider


router = APIRouter(prefix="/veiculos", tags=["veiculos"])


def get_veiculo_service(
    db: AsyncSession = Depends(get_db),
    fx: FxProvider = Depends(get_fx_provider),
) -> VeiculoService:
    return VeiculoService(VeiculoRepository(db), fx)


@router.get("",
            response_model=Page[VeiculoResponse],
            response_model_exclude_none=True
            )
async def listar_veiculos(
    _user=Depends(get_current_user),
    service: VeiculoService = Depends(get_veiculo_service),
    marca: Optional[str] = None,
    ano: Optional[int] = None,
    cor: Optional[str] = None,
    min_preco: Optional[Decimal] = Query(default=None, alias="minPreco"),
    max_preco: Optional[Decimal] = Query(default=None, alias="maxPreco"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    sort_by: str = Query(default="id"),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
) -> Page[VeiculoResponse]:
    result = await service.listar(
        marca=marca,
        ano=ano,
        cor=cor,
        min_preco_usd=min_preco,
        max_preco_usd=max_preco,
        page=page,
        size=size,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )

    return Page[VeiculoResponse](
        items=[to_dto(v) for v in result.items],
        total=result.total,
        page=result.page,
        size=result.size,
    )


@router.get("/{veiculo_id}",
            response_model=VeiculoResponse,
            response_model_exclude_none=True
            )
async def detalhar_veiculo(
    veiculo_id: int,
    _user=Depends(get_current_user),
    service: VeiculoService = Depends(get_veiculo_service),
) -> VeiculoResponse:
    v = await service.obter_por_id(veiculo_id)
    return to_dto(v)


@router.post("", response_model=VeiculoResponse,
             status_code=status.HTTP_201_CREATED,
             response_model_exclude_none=True
             )
async def criar_veiculo(
    payload: VeiculoCreateRequest,
    _admin=Depends(require_admin),
    service: VeiculoService = Depends(get_veiculo_service),
) -> VeiculoResponse:
    v = await service.criar(
        placa=payload.placa,
        marca=payload.marca,
        modelo=payload.modelo,
        ano=payload.ano,
        cor=payload.cor,
        preco_brl=payload.preco_brl,
    )
    return to_dto(v)


@router.put("/{veiculo_id}",
            response_model=VeiculoResponse,
            response_model_exclude_none=True)
async def atualizar_veiculo_put(
    veiculo_id: int,
    payload: VeiculoUpdateRequest,
    _admin=Depends(require_admin),
    service: VeiculoService = Depends(get_veiculo_service),
) -> VeiculoResponse:
    v = await service.atualizar_put(
        veiculo_id,
        marca=payload.marca,
        modelo=payload.modelo,
        ano=payload.ano,
        cor=payload.cor,
        preco_brl=payload.preco_brl,
    )
    return to_dto(v)


@router.patch("/{veiculo_id}",
              response_model=VeiculoResponse,
              response_model_exclude_none=True)
async def atualizar_veiculo_patch(
    veiculo_id: int,
    payload: VeiculoPatchRequest,
    _admin=Depends(require_admin),
    service: VeiculoService = Depends(get_veiculo_service),
) -> VeiculoResponse:
    v = await service.atualizar_patch(
        veiculo_id,
        marca=payload.marca,
        modelo=payload.modelo,
        ano=payload.ano,
        cor=payload.cor,
        preco_brl=payload.preco_brl,
    )
    return to_dto(v)


@router.delete("/{veiculo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_veiculo(
    veiculo_id: int,
    _admin=Depends(require_admin),
    service: VeiculoService = Depends(get_veiculo_service),
) -> None:
    await service.deletar(veiculo_id)
    return None


@router.get("/relatorios/por-marca",
            response_model=List[VeiculoPorMarcaResponse],
            response_model_exclude_none=True)
async def relatorio_por_marca(
    _user=Depends(get_current_user),
    service: VeiculoService = Depends(get_veiculo_service),
) -> list[VeiculoPorMarcaResponse]:
    rows = await service.relatorio_por_marca()
    return [VeiculoPorMarcaResponse(marca=marca, quantidade=qtd) for marca, qtd in rows]
