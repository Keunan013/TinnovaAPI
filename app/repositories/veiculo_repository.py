from sqlalchemy import select, update, func, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from typing import List, Tuple

from app.models.veiculo_model import VeiculoModel
from app.mappers.veiculo_mapper import to_domain
from app.domain.veiculo import Veiculo
from app.domain.veiculo_filter import VeiculoFilter


class VeiculoRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _base_query(self):
        return select(VeiculoModel).where(VeiculoModel.ativo.is_(True))

    async def get_by_id(self, veiculo_id: int) -> Veiculo | None:
        result = await self.session.execute(
            self._base_query().where(VeiculoModel.id == veiculo_id)
        )
        model = result.scalar_one_or_none()
        return to_domain(model) if model else None

    async def get_by_placa(self, placa: str) -> Veiculo | None:
        result = await self.session.execute(
            self._base_query().where(VeiculoModel.placa == placa)
        )
        model = result.scalar_one_or_none()
        return to_domain(model) if model else None

    async def list(
        self,
        *,
        filters: VeiculoFilter,
        page: int,
        size: int,
        sort_by: str,
        sort_dir: str,
    ) -> Tuple[List[Veiculo], int]:

        q = self._base_query()

        if filters.marca:
            q = q.where(VeiculoModel.marca == filters.marca)
        if filters.ano:
            q = q.where(VeiculoModel.ano == filters.ano)
        if filters.cor:
            q = q.where(VeiculoModel.cor == filters.cor)
        if filters.min_preco_usd is not None:
            q = q.where(VeiculoModel.preco_usd >= filters.min_preco_usd)
        if filters.max_preco_usd is not None:
            q = q.where(VeiculoModel.preco_usd <= filters.max_preco_usd)

        count_query = select(func.count()).select_from(q.subquery())
        total = (await self.session.execute(count_query)).scalar_one()

        sort_map = {
            "id": VeiculoModel.id,
            "marca": VeiculoModel.marca,
            "modelo": VeiculoModel.modelo,
            "ano": VeiculoModel.ano,
            "cor": VeiculoModel.cor,
            "preco_usd": VeiculoModel.preco_usd,
        }

        sort_column = sort_map.get(sort_by, VeiculoModel.id)

        if sort_dir.lower() == "desc":
            order = desc(sort_column)
        else:
            order = asc(sort_column)
        q = (
            q.order_by(order)
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.session.execute(q)
        items = [to_domain(model) for model in result.scalars().all()]
        return items, total

    async def add(self, entity: Veiculo) -> Veiculo:
        model = VeiculoModel(
            placa=entity.placa,
            marca=entity.marca,
            modelo=entity.modelo,
            ano=entity.ano,
            cor=entity.cor,
            preco_usd=entity.preco_usd,
            ativo=True,
        )
        self.session.add(model)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise  # services vai traduzir para 409
        await self.session.refresh(model)
        return to_domain(model)

    async def update_fields(
        self,
        veiculo_id: int,
        fields: dict,
    ) -> Veiculo | None:
        await self.session.execute(
            update(VeiculoModel)
            .where(
                VeiculoModel.id == veiculo_id,
                VeiculoModel.ativo.is_(True),
            )
            .values(**fields)
        )
        await self.session.commit()
        return await self.get_by_id(veiculo_id)

    async def soft_delete(self, veiculo_id: int) -> None:
        await self.session.execute(
            update(VeiculoModel)
            .where(VeiculoModel.id == veiculo_id)
            .values(ativo=False)
        )
        await self.session.commit()

    async def relatorio_por_marca(self) -> List[tuple[str, int]]:
        query = (
            select(
                VeiculoModel.marca,
                func.count(VeiculoModel.id),
            )
            .where(VeiculoModel.ativo.is_(True))
            .group_by(VeiculoModel.marca)
            .order_by(func.count(VeiculoModel.id).desc())
        )
        result = await self.session.execute(query)
        rows = result.all()
        return [(marca, quantidade) for marca, quantidade in rows]
