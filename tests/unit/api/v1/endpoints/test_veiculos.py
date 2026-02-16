from __future__ import annotations

import pytest
import pytest_asyncio
import httpx

from decimal import Decimal
from types import SimpleNamespace
from typing import Any, AsyncIterator
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from unittest.mock import AsyncMock
from http import HTTPStatus

from app.api.v1.endpoints.veiculos import router as veiculos_router
from app.api.v1.endpoints.veiculos import get_veiculo_service as dep_get_veiculo_service
from app.api.deps import get_current_user as dep_get_current_user
from app.api.deps import require_admin as dep_require_admin
from app.core.enums.user_role import UserRole
from app.core.schemas.current_user import CurrentUser
from app.domain.veiculo import Veiculo
from app.domain.page_result import PageResult
from app.exceptions.veiculo_exceptions import PlacaDuplicadaError


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


@pytest_asyncio.fixture
async def app() -> AsyncIterator[FastAPI]:
    app_ = FastAPI()
    app_.include_router(veiculos_router)

    async def _override_get_current_user() -> CurrentUser:
        return CurrentUser(email="user@test.com", role=UserRole.USER)

    async def _override_require_admin() -> CurrentUser:
        return CurrentUser(email="admin@test.com", role=UserRole.ADMIN)

    app_.dependency_overrides[dep_get_current_user] = _override_get_current_user
    app_.dependency_overrides[dep_require_admin] = _override_require_admin

    yield app_

    app_.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def service_mock() -> Any:
    svc = SimpleNamespace()
    svc.listar = AsyncMock()
    svc.obter_por_id = AsyncMock()
    svc.criar = AsyncMock()
    svc.atualizar_put = AsyncMock()
    svc.atualizar_patch = AsyncMock()
    svc.deletar = AsyncMock()
    svc.relatorio_por_marca = AsyncMock()
    return svc


@pytest_asyncio.fixture
async def override_service(app: FastAPI, service_mock: Any) -> Any:
    def _override_get_veiculo_service():
        return service_mock

    app.dependency_overrides[dep_get_veiculo_service] = _override_get_veiculo_service
    return service_mock


@pytest.mark.anyio
async def test_listar_veiculos_200(client: httpx.AsyncClient, override_service: Any):
    override_service.listar.return_value = PageResult(
        items=[_veiculo(id=1), _veiculo(id=2)],
        total=2,
        page=1,
        size=10,
    )

    resp = await client.get(
        "/veiculos",
        params={
            "marca": "Ford",
            "ano": 2018,
            "cor": "Preto",
            "minPreco": "100.00",
            "maxPreco": "9999.99",
            "page": 1,
            "size": 10,
            "sort_by": "id",
            "sort_dir": "asc",
        },
    )

    data = resp.json()
    assert resp.status_code == HTTPStatus.OK
    assert data["total"] == 2
    assert data["page"] == 1
    assert data["size"] == 10
    assert len(data["items"]) == 2
    override_service.listar.assert_awaited_once()
    _, kwargs = override_service.listar.await_args
    assert kwargs["marca"] == "Ford"
    assert kwargs["ano"] == 2018
    assert kwargs["cor"] == "Preto"
    assert Decimal(kwargs["min_preco_usd"]) == Decimal("100.00")
    assert Decimal(kwargs["max_preco_usd"]) == Decimal("9999.99")
    assert kwargs["page"] == 1
    assert kwargs["size"] == 10


@pytest.mark.anyio
async def test_detalhar_veiculo_200(client: httpx.AsyncClient, override_service: Any):
    override_service.obter_por_id.return_value = _veiculo(id=10, placa="ZZZ9Z99")

    resp = await client.get("/veiculos/10")

    data = resp.json()

    override_service.obter_por_id.assert_awaited_once_with(10)
    assert resp.status_code == HTTPStatus.OK
    assert data["id"] == 10
    assert data["placa"] == "ZZZ9Z99"


@pytest.mark.anyio
async def test_criar_veiculo_201_quando_admin(client: httpx.AsyncClient, app: FastAPI, override_service: Any):
    override_service.criar.return_value = _veiculo(id=1, placa="AAA0A00")

    payload = {
        "placa": "AAA0A00",
        "marca": "VW",
        "modelo": "Gol",
        "ano": 2020,
        "cor": "Branco",
        "preco_brl": "50000.00",
    }

    resp = await client.post("/veiculos", json=payload)

    data = resp.json()
    assert resp.status_code == HTTPStatus.CREATED
    assert data["id"] == 1
    assert data["placa"] == "AAA0A00"
    override_service.criar.assert_awaited_once()
    _, kwargs = override_service.criar.await_args
    assert kwargs["placa"] == "AAA0A00"
    assert Decimal(kwargs["preco_brl"]) == Decimal("50000.00")


@pytest.mark.anyio
async def test_criar_veiculo_409_quando_integrity_error(
    client: httpx.AsyncClient,
    app: FastAPI,
    override_service: Any,
    monkeypatch: pytest.MonkeyPatch,
):
    from sqlalchemy.exc import IntegrityError

    override_service.criar.side_effect = IntegrityError("stmt", "params", "orig")

    app.add_exception_handler(
        PlacaDuplicadaError,
        lambda *_: JSONResponse(status_code=HTTPStatus.CONFLICT, content={"ok": False}),
    )

    payload = {
        "placa": "DUPL123",
        "marca": "Ford",
        "modelo": "Ka",
        "ano": 2020,
        "cor": "Preto",
        "preco_brl": "1000.00",
    }

    resp = await client.post("/veiculos", json=payload)

    assert resp.status_code == HTTPStatus.CONFLICT
    assert resp.json() == {"ok": False}


@pytest.mark.anyio
async def test_atualizar_put_200(client: httpx.AsyncClient, app: FastAPI, override_service: Any):
    override_service.atualizar_put.return_value = _veiculo(id=5, cor="Azul")

    payload = {
        "marca": "Ford",
        "modelo": "Ka",
        "ano": 2017,
        "cor": "Azul",
        "preco_brl": "30000.00",
    }

    resp = await client.put("/veiculos/5", json=payload)

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["id"] == 5
    assert resp.json()["cor"] == "Azul"
    override_service.atualizar_put.assert_awaited_once()
    args, kwargs = override_service.atualizar_put.await_args
    assert args[0] == 5
    assert kwargs["cor"] == "Azul"
    assert Decimal(kwargs["preco_brl"]) == Decimal("30000.00")


@pytest.mark.anyio
async def test_atualizar_patch_200(client: httpx.AsyncClient, app: FastAPI, override_service: Any):
    override_service.atualizar_patch.return_value = _veiculo(id=7, cor="Prata")

    payload = {
        "cor": "Prata",
        "preco_brl": "12345.67",
    }

    resp = await client.patch("/veiculos/7", json=payload)

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["id"] == 7
    assert resp.json()["cor"] == "Prata"
    override_service.atualizar_patch.assert_awaited_once()
    args, kwargs = override_service.atualizar_patch.await_args
    assert args[0] == 7
    assert kwargs["cor"] == "Prata"
    assert Decimal(kwargs["preco_brl"]) == Decimal("12345.67")


@pytest.mark.anyio
async def test_deletar_204(client: httpx.AsyncClient, app: FastAPI, override_service: Any):
    override_service.deletar.return_value = None

    resp = await client.delete("/veiculos/9")

    assert resp.status_code == HTTPStatus.NO_CONTENT
    override_service.deletar.assert_awaited_once_with(9)


@pytest.mark.anyio
async def test_relatorio_por_marca_200(client: httpx.AsyncClient, override_service: Any):
    override_service.relatorio_por_marca.return_value = [("Ford", 2), ("VW", 1)]

    resp = await client.get("/veiculos/relatorios/por-marca")

    data = resp.json()
    override_service.relatorio_por_marca.assert_awaited_once()
    assert resp.status_code == HTTPStatus.OK
    assert data == [{"marca": "Ford", "quantidade": 2}, {"marca": "VW", "quantidade": 1}]
