from __future__ import annotations

import pytest

from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, List, Optional
from unittest.mock import AsyncMock, MagicMock

from app.domain.veiculo import Veiculo
from app.domain.veiculo_filter import VeiculoFilter
from app.repositories.veiculo_repository import VeiculoRepository


# fake SQLAlchemy result
@dataclass
class _ScalarsResult:
    _items: List[Any]

    def all(self) -> List[Any]:
        return self._items


class _ExecuteResult:
    """
    Retorno do session.execute(...)
    - scalar_one_or_none()
    - scalar_one()
    - scalars().all()
    """

    def __init__(
        self,
        *,
        scalar_one_or_none: Any = None,
        scalar_one: Any = None,
        scalars_items: Optional[List[Any]] = None,
    ):
        self._scalar_one_or_none = scalar_one_or_none
        self._scalar_one = scalar_one
        self._scalars_items = scalars_items or []

    def scalar_one_or_none(self) -> Any:
        return self._scalar_one_or_none

    def scalar_one(self) -> Any:
        return self._scalar_one

    def scalars(self) -> _ScalarsResult:
        return _ScalarsResult(self._scalars_items)


@pytest.fixture
def session_mock() -> MagicMock:
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def repo(session_mock: MagicMock) -> VeiculoRepository:
    return VeiculoRepository(session_mock)


@pytest.mark.asyncio
async def test_get_by_id_returns_domain(repo: VeiculoRepository, session_mock: MagicMock, monkeypatch):
    import app.repositories.veiculo_repository as repo_module

    fake_model = SimpleNamespace(
        id=1,
        placa="ABC1234",
        marca="Ford",
        modelo="Ka",
        ano=2020,
        cor="Preto",
        preco_usd=Decimal("1000.00"),
        ativo=True,
        created_at=None,
        updated_at=None,
    )

    expected = Veiculo(
        id=1,
        placa="ABC1234",
        marca="Ford",
        modelo="Ka",
        ano=2020,
        cor="Preto",
        preco_usd=Decimal("1000.00"),
        ativo=True,
    )

    session_mock.execute.return_value = _ExecuteResult(scalar_one_or_none=fake_model)

    monkeypatch.setattr(repo_module, "to_domain", lambda m: expected)

    got = await repo.get_by_id(1)

    assert expected == got


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_not_found(repo: VeiculoRepository, session_mock: MagicMock):
    session_mock.execute.return_value = _ExecuteResult(scalar_one_or_none=None)
    got = await repo.get_by_id(999)
    assert got is None


@pytest.mark.asyncio
async def test_get_by_placa_returns_domain(repo: VeiculoRepository, session_mock: MagicMock, monkeypatch):
    import app.repositories.veiculo_repository as repo_module

    fake_model = SimpleNamespace(
        id=2,
        placa="ZZZ9999",
        marca="VW",
        modelo="Gol",
        ano=2018,
        cor="Branco",
        preco_usd=Decimal("2000.00"),
        ativo=True,
        created_at=None,
        updated_at=None,
    )

    expected = Veiculo(
        id=2,
        placa="ZZZ9999",
        marca="VW",
        modelo="Gol",
        ano=2018,
        cor="Branco",
        preco_usd=Decimal("2000.00"),
        ativo=True,
    )

    session_mock.execute.return_value = _ExecuteResult(scalar_one_or_none=fake_model)
    monkeypatch.setattr(repo_module, "to_domain", lambda m: expected)

    got = await repo.get_by_placa("ZZZ9999")

    assert expected == got


@pytest.mark.asyncio
async def test_get_by_placa_returns_none_when_not_found(repo: VeiculoRepository, session_mock: MagicMock):
    session_mock.execute.return_value = _ExecuteResult(scalar_one_or_none=None)
    got = await repo.get_by_placa("NOTFOUND")
    assert got is None


@pytest.mark.asyncio
async def test_list_applies_filters_sort_and_pagination(repo: VeiculoRepository, session_mock: MagicMock, monkeypatch):
    import app.repositories.veiculo_repository as repo_module

    # 1) count query
    # 2) items query
    session_mock.execute.side_effect = [
        _ExecuteResult(scalar_one=2),  # total
        _ExecuteResult(scalars_items=[object(), object()]),  # models
    ]

    monkeypatch.setattr(
        repo_module,
        "to_domain",
        lambda m: Veiculo(
            id=1,
            placa="A",
            marca="Ford",
            modelo="Ka",
            ano=2020,
            cor="Preto",
            preco_usd=Decimal("10.00"),
            ativo=True,
        ),
    )

    filters = VeiculoFilter(
        marca="Ford",
        ano=2020,
        cor="Preto",
        min_preco_usd=Decimal("5.00"),
        max_preco_usd=Decimal("20.00"),
    )

    items, total = await repo.list(
        filters=filters,
        page=2,
        size=10,
        sort_by="preco_usd",
        sort_dir="desc",
    )

    assert all(isinstance(v, Veiculo) for v in items)
    assert 2 == total
    assert 2 == len(items)
    assert 2 == session_mock.execute.await_count


@pytest.mark.asyncio
async def test_update_fields_commits_and_returns_updated(repo: VeiculoRepository, session_mock: MagicMock, monkeypatch):
    import app.repositories.veiculo_repository as repo_module

    # update_fields chama:
    # 1) session.execute(update...)
    # 2) session.commit()
    # 3) get_by_id(...) -> session.execute(select...) e mapper
    fake_model = SimpleNamespace(
        id=10,
        placa="ABC1234",
        marca="Ford",
        modelo="Ka",
        ano=2021,
        cor="Azul",
        preco_usd=Decimal("999.99"),
        ativo=True,
        created_at=None,
        updated_at=None,
    )

    session_mock.execute.side_effect = [
        _ExecuteResult(),  # update
        _ExecuteResult(scalar_one_or_none=fake_model),  # select
    ]

    expected = Veiculo(
        id=10,
        placa="ABC1234",
        marca="Ford",
        modelo="Ka",
        ano=2021,
        cor="Azul",
        preco_usd=Decimal("999.99"),
        ativo=True,
    )
    monkeypatch.setattr(repo_module, "to_domain", lambda m: expected)

    got = await repo.update_fields(10, {"cor": "Azul", "ano": 2021})

    session_mock.commit.assert_awaited_once()
    assert expected == got
    assert 2 == session_mock.execute.await_count


@pytest.mark.asyncio
async def test_soft_delete_commits(repo: VeiculoRepository, session_mock: MagicMock):
    session_mock.execute.return_value = _ExecuteResult()
    await repo.soft_delete(10)
    session_mock.commit.assert_awaited_once()
    session_mock.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_relatorio_por_marca_returns_rows(repo: VeiculoRepository, session_mock: MagicMock):
    class _AllResult:
        def all(self):
            return [("Ford", 2), ("VW", 1)]

    session_mock.execute.return_value = _AllResult()

    rows = await repo.relatorio_por_marca()

    assert rows == [("Ford", 2), ("VW", 1)]


@pytest.mark.asyncio
async def test_add_commits_refreshes_and_returns_domain(repo: VeiculoRepository, session_mock: MagicMock, monkeypatch):
    import app.repositories.veiculo_repository as repo_module

    added_models: list[Any] = []

    def _add_side_effect(model: Any):
        added_models.append(model)

    async def _refresh_side_effect(model: Any):
        setattr(model, "id", 1)

    session_mock.add.side_effect = _add_side_effect
    session_mock.commit.return_value = None
    session_mock.refresh.side_effect = _refresh_side_effect

    expected = Veiculo(
        id=1,
        placa="ABC1234",
        marca="Ford",
        modelo="Ka",
        ano=2020,
        cor="Preto",
        preco_usd=Decimal("100.00"),
        ativo=True,
    )
    monkeypatch.setattr(repo_module, "to_domain", lambda m: expected)

    entity = Veiculo(
        id=None,
        placa="ABC1234",
        marca="Ford",
        modelo="Ka",
        ano=2020,
        cor="Preto",
        preco_usd=Decimal("100.00"),
        ativo=True,
    )

    got = await repo.add(entity)

    session_mock.add.assert_called_once()
    session_mock.commit.assert_awaited_once()
    session_mock.refresh.assert_awaited_once()
    assert expected == got
    assert added_models, "Esperava capturar o model adicionado"
    assert 1 == getattr(added_models[0], "id", None)


@pytest.mark.asyncio
async def test_add_rolls_back_on_integrity_error(repo: VeiculoRepository, session_mock: MagicMock):
    from sqlalchemy.exc import IntegrityError

    session_mock.commit.side_effect = IntegrityError("stmt", "params", "orig")

    entity = Veiculo(
        id=None,
        placa="DUPL123",
        marca="Ford",
        modelo="Ka",
        ano=2020,
        cor="Preto",
        preco_usd=Decimal("100.00"),
        ativo=True,
    )

    with pytest.raises(IntegrityError):
        await repo.add(entity)

    session_mock.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_uses_asc_when_sort_dir_not_desc(repo: VeiculoRepository, session_mock: MagicMock, monkeypatch):
    import app.repositories.veiculo_repository as repo_module

    # 1) count
    # 2) items
    session_mock.execute.side_effect = [
        _ExecuteResult(scalar_one=1),
        _ExecuteResult(scalars_items=[object()]),
    ]

    monkeypatch.setattr(
        repo_module,
        "to_domain",
        lambda m: Veiculo(
            id=1,
            placa="A",
            marca="Ford",
            modelo="Ka",
            ano=2020,
            cor="Preto",
            preco_usd=Decimal("10.00"),
            ativo=True,
        ),
    )

    filters = VeiculoFilter()

    items, total = await repo.list(
        filters=filters,
        page=1,
        size=10,
        sort_by="id",
        sort_dir="asc",
    )

    assert total == 1
    assert len(items) == 1
    assert 2 == session_mock.execute.await_count
