from decimal import Decimal
from typing import Optional, Dict

from app.domain.veiculo import Veiculo
from app.domain.veiculo_filter import VeiculoFilter
from app.domain.page_result import PageResult
from app.repositories.veiculo_repository import VeiculoRepository
from app.services.fx.fx_provider import FxProvider
from app.exceptions.veiculo_exceptions import (
    InvalidUpdateError,
    PlacaDuplicadaError,
    VeiculoNaoEncontradoError,
)


class VeiculoService:
    def __init__(self, repository: VeiculoRepository, fx: FxProvider):
        self.repository = repository
        self.fx = fx

    async def obter_por_id(self, veiculo_id: int) -> Veiculo:
        veiculo = await self.repository.get_by_id(veiculo_id)
        if not veiculo:
            raise VeiculoNaoEncontradoError()
        return veiculo

    async def listar(
        self,
        *,
        marca: Optional[str] = None,
        ano: Optional[int] = None,
        cor: Optional[str] = None,
        min_preco_usd: Optional[Decimal] = None,
        max_preco_usd: Optional[Decimal] = None,
        page: int = 1,
        size: int = 10,
        sort_by: str = "id",
        sort_dir: str = "asc",
    ) -> PageResult:
        if page < 1:
            raise InvalidUpdateError("page deve ser >= 1")
        if size < 1 or size > 100:
            raise InvalidUpdateError("size deve estar entre 1 e 100")

        if (
            min_preco_usd is not None
            and max_preco_usd is not None
            and min_preco_usd > max_preco_usd
        ):
            raise InvalidUpdateError("minPreco não pode ser maior que maxPreco")

        filters = VeiculoFilter(
            marca=marca,
            ano=ano,
            cor=cor,
            min_preco_usd=min_preco_usd,
            max_preco_usd=max_preco_usd,
        )

        items, total = await self.repository.list(
            filters=filters,
            page=page,
            size=size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        return PageResult(items=items, total=total, page=page, size=size)

    async def relatorio_por_marca(self) -> list[tuple[str, int]]:
        return await self.repository.relatorio_por_marca()

    async def criar(
        self,
        *,
        placa: str,
        marca: str,
        modelo: str,
        ano: int,
        cor: str,
        preco_brl: Decimal,
    ) -> Veiculo:
        existente = await self.repository.get_by_placa(placa)
        if existente:
            raise PlacaDuplicadaError()

        preco_usd = await self.fx.brl_to_usd(preco_brl)

        veiculo = Veiculo(
            id=None,
            placa=placa,
            marca=marca,
            modelo=modelo,
            ano=ano,
            cor=cor,
            preco_usd=preco_usd,
            ativo=True,
        )
        return await self.repository.add(veiculo)

    async def atualizar_put(
        self,
        veiculo_id: int,
        *,
        marca: str,
        modelo: str,
        ano: int,
        cor: str,
        preco_brl: Decimal,
    ) -> Veiculo:
        atual = await self.repository.get_by_id(veiculo_id)
        if not atual:
            raise VeiculoNaoEncontradoError()

        preco_usd = await self.fx.brl_to_usd(preco_brl)

        atualizado = await self.repository.update_fields(
            veiculo_id,
            {
                "marca": marca,
                "modelo": modelo,
                "ano": ano,
                "cor": cor,
                "preco_usd": preco_usd,
            },
        )
        if not atualizado:
            raise VeiculoNaoEncontradoError()
        return atualizado

    async def atualizar_patch(
        self,
        veiculo_id: int,
        *,
        marca: Optional[str] = None,
        modelo: Optional[str] = None,
        ano: Optional[int] = None,
        cor: Optional[str] = None,
        preco_brl: Optional[Decimal] = None,
    ) -> Veiculo:
        atual = await self.repository.get_by_id(veiculo_id)
        if not atual:
            raise VeiculoNaoEncontradoError()

        fields: Dict = {}
        if marca is not None:
            fields["marca"] = marca
        if modelo is not None:
            fields["modelo"] = modelo
        if ano is not None:
            fields["ano"] = ano
        if cor is not None:
            fields["cor"] = cor
        if preco_brl is not None:
            fields["preco_usd"] = await self.fx.brl_to_usd(preco_brl)

        if not fields:
            raise InvalidUpdateError("PATCH sem campos para atualizar")

        atualizado = await self.repository.update_fields(veiculo_id, fields)
        if not atualizado:
            raise VeiculoNaoEncontradoError()
        return atualizado

    # Soft delete
    async def deletar(self, veiculo_id: int) -> None:
        veiculo = await self.repository.get_by_id(veiculo_id)
        if not veiculo:
            raise VeiculoNaoEncontradoError()
        await self.repository.soft_delete(veiculo_id)
