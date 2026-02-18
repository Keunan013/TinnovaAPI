from __future__ import annotations

import pytest

from decimal import Decimal
from unittest.mock import AsyncMock

from app.domain.veiculo import Veiculo
from app.domain.veiculo_filter import VeiculoFilter
from app.services.veiculo_service import VeiculoService
from app.exceptions.veiculo_exceptions import (
    InvalidUpdateError,
    PlacaDuplicadaError,
    VeiculoNaoEncontradoError,
)


def _veiculo(
    *,
    id: int = 1,
    placa: str = "ABC1D23",
    marca: str = "Ford",
    modelo: str = "Fiesta",
    ano: int = 2018,
    cor: str = "Preto",
    preco_usd: Decimal = Decimal("1000.00"),
    ativo: bool = True,
) -> Veiculo:
    return Veiculo(
        id=id,
        placa=placa,
        marca=marca,
        modelo=modelo,
        ano=ano,
        cor=cor,
        preco_usd=preco_usd,
        ativo=ativo,
    )


@pytest.mark.anyio
async def test_criar_deve_falhar_quando_placa_ja_existe():
    # Arrange
    repo = AsyncMock()
    fx = AsyncMock()
    service = VeiculoService(repo, fx)

    repo.get_by_placa.return_value = _veiculo(placa="AAA0A00")

    # Act / Assert
    with pytest.raises(PlacaDuplicadaError):
        await service.criar(
            placa="AAA0A00",
            marca="VW",
            modelo="Gol",
            ano=2020,
            cor="Branco",
            preco_brl=Decimal("50000"),
        )

    repo.add.assert_not_awaited()
    fx.brl_to_usd.assert_not_awaited()


@pytest.mark.anyio
async def test_criar_deve_converter_brl_para_usd_e_salvar():
    # Arrange
    repo = AsyncMock()
    fx = AsyncMock()
    service = VeiculoService(repo, fx)

    repo.get_by_placa.return_value = None
    fx.brl_to_usd.return_value = Decimal("10000.00")

    saved = _veiculo(id=123, placa="ZZZ9Z99", preco_usd=Decimal("10000.00"))
    repo.add.return_value = saved

    # Act
    result = await service.criar(
        placa="ZZZ9Z99",
        marca="Fiat",
        modelo="Uno",
        ano=2015,
        cor="Vermelho",
        preco_brl=Decimal("50000.00"),
    )

    # Assert
    fx.brl_to_usd.assert_awaited_once_with(Decimal("50000.00"))
    repo.add.assert_awaited_once()
    assert result.id == 123
    assert result.preco_usd == Decimal("10000.00")


@pytest.mark.anyio
async def test_listar_deve_passar_filtros_combinados_para_repo():
    # Arrange
    repo = AsyncMock()
    fx = AsyncMock()
    service = VeiculoService(repo, fx)

    repo.list.return_value = ([_veiculo(id=1), _veiculo(id=2)], 2)

    # Act
    page = await service.listar(
        marca="Ford",
        ano=2018,
        cor="Preto",
        min_preco_usd=Decimal("100.00"),
        max_preco_usd=Decimal("999.99"),
        page=2,
        size=10,
        sort_by="preco_usd",
        sort_dir="desc",
    )

    # Assert
    assert page.total == 2
    assert page.page == 2
    assert page.size == 10
    assert len(page.items) == 2
    repo.list.assert_awaited_once()
    _, kwargs = repo.list.await_args
    assert kwargs["page"] == 2
    assert kwargs["size"] == 10
    assert kwargs["sort_by"] == "preco_usd"
    assert kwargs["sort_dir"] == "desc"
    filters = kwargs["filters"]
    assert isinstance(filters, VeiculoFilter)
    assert filters.marca == "Ford"
    assert filters.ano == 2018
    assert filters.cor == "Preto"
    assert filters.min_preco_usd == Decimal("100.00")
    assert filters.max_preco_usd == Decimal("999.99")


@pytest.mark.anyio
async def test_listar_deve_falhar_quando_page_invalido():
    # Arrange
    repo = AsyncMock()
    fx = AsyncMock()
    service = VeiculoService(repo, fx)

    # Act / Assert
    with pytest.raises(InvalidUpdateError):
        await service.listar(page=0)

    repo.list.assert_not_awaited()


@pytest.mark.anyio
async def test_listar_deve_falhar_quando_size_invalido():
    # Arrange
    repo = AsyncMock()
    fx = AsyncMock()
    service = VeiculoService(repo, fx)

    # Act / Assert
    with pytest.raises(InvalidUpdateError):
        await service.listar(size=0)

    with pytest.raises(InvalidUpdateError):
        await service.listar(size=101)

    repo.list.assert_not_awaited()


@pytest.mark.anyio
async def test_listar_deve_falhar_quando_min_maior_que_max():
    # Arrange
    repo = AsyncMock()
    fx = AsyncMock()
    service = VeiculoService(repo, fx)

    # Act / Assert
    with pytest.raises(InvalidUpdateError):
        await service.listar(
            min_preco_usd=Decimal("10.00"),
            max_preco_usd=Decimal("1.00"),
        )

    repo.list.assert_not_awaited()


@pytest.mark.anyio
async def test_atualizar_put_deve_falhar_quando_veiculo_nao_existe():
    # Arrange
    repo = AsyncMock()
    fx = AsyncMock()
    service = VeiculoService(repo, fx)

    repo.get_by_id.return_value = None

    # Act / Assert
    with pytest.raises(VeiculoNaoEncontradoError):
        await service.atualizar_put(
            999,
            marca="Ford",
            modelo="Ka",
            ano=2017,
            cor="Prata",
            preco_brl=Decimal("30000"),
        )

    repo.update_fields.assert_not_awaited()


@pytest.mark.anyio
async def test_atualizar_patch_sem_campos_deve_falhar_e_nao_chamar_repo_update():
    # Arrange
    repo = AsyncMock()
    fx = AsyncMock()
    service = VeiculoService(repo, fx)

    repo.get_by_id.return_value = _veiculo(id=1)

    # Act / Assert
    with pytest.raises(InvalidUpdateError):
        await service.atualizar_patch(1)

    repo.update_fields.assert_not_awaited()
    fx.brl_to_usd.assert_not_awaited()


@pytest.mark.anyio
async def test_obter_por_id_deve_levantar_quando_nao_encontrar():
    # Arrange
    repo = AsyncMock()
    fx = AsyncMock()
    service = VeiculoService(repo, fx)
    repo.get_by_id.return_value = None

    # Act / Assert
    with pytest.raises(VeiculoNaoEncontradoError):
        await service.obter_por_id(999)


@pytest.mark.anyio
async def test_obter_por_id_deve_retornar_quando_encontrar():
    # Arrange
    repo = AsyncMock()
    fx = AsyncMock()
    service = VeiculoService(repo, fx)
    repo.get_by_id.return_value = _veiculo(id=1)

    # Act
    v = await service.obter_por_id(1)

    # Assert
    assert v.id == 1


@pytest.mark.anyio
async def test_relatorio_por_marca_deve_delegar_para_repo():
    # Arrange
    repo = AsyncMock()
    fx = AsyncMock()
    service = VeiculoService(repo, fx)
    repo.relatorio_por_marca.return_value = [("Ford", 2), ("VW", 1)]

    # Act
    rows = await service.relatorio_por_marca()

    # Assert
    assert rows == [("Ford", 2), ("VW", 1)]
    repo.relatorio_por_marca.assert_awaited_once()


@pytest.mark.anyio
async def test_atualizar_put_deve_converter_preco_e_atualizar_e_retornar():
    # Arrange
    repo = AsyncMock()
    fx = AsyncMock()
    service = VeiculoService(repo, fx)

    repo.get_by_id.return_value = _veiculo(id=10, preco_usd=Decimal("1.00"))
    fx.brl_to_usd.return_value = Decimal("999.99")

    updated = _veiculo(id=10, cor="Azul", ano=2021, preco_usd=Decimal("999.99"))
    repo.update_fields.return_value = updated

    # Act
    out = await service.atualizar_put(
        10,
        marca="Ford",
        modelo="Ka",
        ano=2021,
        cor="Azul",
        preco_brl=Decimal("5000.00"),
    )

    # Assert
    fx.brl_to_usd.assert_awaited_once_with(Decimal("5000.00"))
    repo.update_fields.assert_awaited_once()
    args, kwargs = repo.update_fields.await_args
    assert args[0] == 10
    assert kwargs == {}
    fields = args[1]
    assert fields["preco_usd"] == Decimal("999.99")
    assert out.preco_usd == Decimal("999.99")
    assert out.cor == "Azul"
    assert out.ano == 2021


@pytest.mark.anyio
async def test_atualizar_put_deve_levantar_se_repo_update_retornar_none():
    # Arrange
    repo = AsyncMock()
    fx = AsyncMock()
    service = VeiculoService(repo, fx)

    repo.get_by_id.return_value = _veiculo(id=10)
    fx.brl_to_usd.return_value = Decimal("10.00")
    repo.update_fields.return_value = None  # <- cobre o if not atualizado

    # Act / Assert
    with pytest.raises(VeiculoNaoEncontradoError):
        await service.atualizar_put(
            10,
            marca="Ford",
            modelo="Ka",
            ano=2021,
            cor="Azul",
            preco_brl=Decimal("50.00"),
        )


@pytest.mark.anyio
async def test_atualizar_patch_deve_levantar_quando_veiculo_nao_existe():
    # Arrange
    repo = AsyncMock()
    fx = AsyncMock()
    service = VeiculoService(repo, fx)
    repo.get_by_id.return_value = None

    # Act / Assert
    with pytest.raises(VeiculoNaoEncontradoError):
        await service.atualizar_patch(999, marca="Ford")


@pytest.mark.anyio
async def test_atualizar_patch_deve_atualizar_campos_parciais_sem_preco():
    # Arrange
    repo = AsyncMock()
    fx = AsyncMock()
    service = VeiculoService(repo, fx)

    repo.get_by_id.return_value = _veiculo(id=1, marca="Ford", modelo="Fiesta")
    updated = _veiculo(id=1, marca="VW", modelo="Gol")
    repo.update_fields.return_value = updated

    # Act
    out = await service.atualizar_patch(1, marca="VW", modelo="Gol")

    # Assert
    repo.update_fields.assert_awaited_once()
    (vid, fields), _ = repo.update_fields.await_args
    assert vid == 1
    assert fields == {"marca": "VW", "modelo": "Gol"}
    fx.brl_to_usd.assert_not_awaited()
    assert out.marca == "VW"
    assert out.modelo == "Gol"


@pytest.mark.anyio
async def test_atualizar_patch_deve_converter_preco_quando_enviado():
    # Arrange
    repo = AsyncMock()
    fx = AsyncMock()
    service = VeiculoService(repo, fx)

    repo.get_by_id.return_value = _veiculo(id=1)
    fx.brl_to_usd.return_value = Decimal("123.45")
    repo.update_fields.return_value = _veiculo(id=1, preco_usd=Decimal("123.45"))

    # Act
    out = await service.atualizar_patch(1, preco_brl=Decimal("617.25"))

    # Assert
    fx.brl_to_usd.assert_awaited_once_with(Decimal("617.25"))
    (vid, fields), _ = repo.update_fields.await_args
    assert vid == 1
    assert fields == {"preco_usd": Decimal("123.45")}
    assert out.preco_usd == Decimal("123.45")


@pytest.mark.anyio
async def test_atualizar_patch_deve_levantar_se_repo_update_retornar_none():
    # Arrange
    repo = AsyncMock()
    fx = AsyncMock()
    service = VeiculoService(repo, fx)

    repo.get_by_id.return_value = _veiculo(id=1)
    repo.update_fields.return_value = None  # <- cobre o if not atualizado

    # Act / Assert
    with pytest.raises(VeiculoNaoEncontradoError):
        await service.atualizar_patch(1, marca="Ford")


@pytest.mark.anyio
async def test_desativar_deve_levantar_quando_nao_encontrar():
    # Arrange
    repo = AsyncMock()
    fx = AsyncMock()
    service = VeiculoService(repo, fx)

    repo.get_by_id.return_value = None

    # Act / Assert
    with pytest.raises(VeiculoNaoEncontradoError):
        await service.desativar(999)

    repo.soft_delete.assert_not_awaited()


@pytest.mark.anyio
async def test_desativar_deve_chamar_soft_delete_quando_encontrar():
    # Arrange
    repo = AsyncMock()
    fx = AsyncMock()
    service = VeiculoService(repo, fx)

    repo.get_by_id.return_value = _veiculo(id=10)

    # Act
    await service.desativar(10)

    # Assert
    repo.soft_delete.assert_awaited_once_with(10)


@pytest.mark.anyio
async def test_atualizar_patch_deve_incluir_ano_quando_informado():
    repo = AsyncMock()
    fx = AsyncMock()
    service = VeiculoService(repo, fx)

    repo.get_by_id.return_value = _veiculo(id=1, ano=2018)
    repo.update_fields.return_value = _veiculo(id=1, ano=2022)

    out = await service.atualizar_patch(1, ano=2022)

    (vid, fields), _ = repo.update_fields.await_args
    assert vid == 1
    assert fields == {"ano": 2022}
    assert out.ano == 2022


@pytest.mark.anyio
async def test_atualizar_patch_deve_incluir_cor_quando_informado():
    repo = AsyncMock()
    fx = AsyncMock()
    service = VeiculoService(repo, fx)

    repo.get_by_id.return_value = _veiculo(id=1, cor="Preto")
    repo.update_fields.return_value = _veiculo(id=1, cor="Branco")

    out = await service.atualizar_patch(1, cor="Branco")

    (vid, fields), _ = repo.update_fields.await_args
    assert vid == 1
    assert fields == {"cor": "Branco"}
    assert out.cor == "Branco"
