from __future__ import annotations

import pytest
import pytest_asyncio
import httpx

from types import SimpleNamespace
from typing import Any, AsyncIterator
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from http import HTTPStatus
from unittest.mock import AsyncMock
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.endpoints.auth import router as auth_router
from app.api.deps import require_admin as dep_require_admin
from app.api.deps import get_user_service as dep_get_user_service
from app.core.enums.error_code import ErrorCode
from app.core.infra import get_redis as dep_get_redis
from app.core.enums.user_role import UserRole
from app.core.schemas.current_user import CurrentUser
from app.exceptions.request_exceptions import TooManyRequestsError
from app.exceptions.user_exceptions import (
    CredenciaisInvalidasError,
    EmailDuplicadoError,
    UserNaoEncontradoError, EmailInvalidoError, SenhaInvalidaError,
)


@pytest_asyncio.fixture
async def app() -> AsyncIterator[FastAPI]:
    app_ = FastAPI()
    app_.include_router(auth_router)

    @app_.exception_handler(StarletteHTTPException)
    async def _http_exc_handler(_, exc: StarletteHTTPException):
        if isinstance(exc.detail, dict):
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    async def _override_require_admin() -> CurrentUser:
        return CurrentUser(email="admin@test.com", role=UserRole.ADMIN)

    app_.dependency_overrides[dep_require_admin] = _override_require_admin

    yield app_
    app_.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def redis_mock() -> Any:
    """
    Fake Redis.
    """
    r = SimpleNamespace()
    r.get = AsyncMock(return_value=None)
    r.set = AsyncMock(return_value=True)
    r.incr = AsyncMock(return_value=1)
    r.expire = AsyncMock(return_value=True)
    r.ttl = AsyncMock(return_value=-1)
    r.delete = AsyncMock(return_value=1)
    return r


@pytest.fixture
def user_service_mock() -> Any:
    svc = SimpleNamespace()
    svc.criar = AsyncMock()
    svc.autenticar = AsyncMock()
    svc.desativar = AsyncMock()
    svc.atualizar_role = AsyncMock()
    return svc


@pytest_asyncio.fixture
async def overrides(app: FastAPI, redis_mock: Any, user_service_mock: Any) -> Any:
    async def _override_get_redis():
        yield redis_mock

    def _override_get_user_service():
        return user_service_mock

    app.dependency_overrides[dep_get_redis] = _override_get_redis
    app.dependency_overrides[dep_get_user_service] = _override_get_user_service
    return user_service_mock


@pytest.mark.anyio
async def test_register_201(client: httpx.AsyncClient, overrides: Any, monkeypatch: pytest.MonkeyPatch):
    created_user = SimpleNamespace(id=1, email="x@test.com", role=UserRole.USER, ativo=True)
    overrides.criar.return_value = created_user

    resp = await client.post(
        "/auth/register",
        json={"email": "x@test.com", "senha": "Senha@123", "role": "USER"},
    )

    data = resp.json()
    assert resp.status_code == HTTPStatus.CREATED
    assert data["id"] == 1
    assert data["email"] == "x@test.com"
    assert data["role"] == "USER"
    assert data["ativo"] is True

    overrides.criar.assert_awaited_once()


@pytest.mark.anyio
async def test_register_409_quando_email_duplicado(client: httpx.AsyncClient, overrides: Any):
    overrides.criar.side_effect = EmailDuplicadoError()

    resp = await client.post(
        "/auth/register",
        json={"email": "x@test.com", "senha": "Senha@123", "role": "USER"},
    )

    body = resp.json()

    assert resp.status_code == HTTPStatus.CONFLICT
    assert "error" in body
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.anyio
async def test_login_200_retorna_token(client: httpx.AsyncClient, overrides: Any, monkeypatch: pytest.MonkeyPatch):
    from app.api.v1.endpoints import auth as auth_module

    monkeypatch.setattr(auth_module, "create_access_token", lambda payload: "test-token")

    overrides.autenticar.return_value = SimpleNamespace(email="user@test.com", role=UserRole.USER)

    resp = await client.post("/auth/login", json={"email": "user@test.com", "senha": "x"})

    overrides.autenticar.assert_awaited_once()
    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["access_token"] == "test-token"


@pytest.mark.anyio
async def test_login_401_quando_credenciais_invalidas(client: httpx.AsyncClient, overrides: Any):
    overrides.autenticar.side_effect = CredenciaisInvalidasError()

    resp = await client.post("/auth/login", json={"email": "user@test.com", "senha": "wrong"})
    assert resp.status_code == HTTPStatus.UNAUTHORIZED

    body = resp.json()

    assert body["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.anyio
async def test_login_429_quando_rate_limited(client: httpx.AsyncClient, overrides: Any, monkeypatch: pytest.MonkeyPatch):
    from app.api.v1.endpoints import auth as auth_module

    class _FakeTooMany(Exception):
        def __init__(self, retry_after_seconds: int):
            self.retry_after_seconds = retry_after_seconds

    # Substitui a classe
    monkeypatch.setattr(auth_module, "TooManyRequestsError", _FakeTooMany)

    # Substitui LoginRateLimiter
    class _FakeLimiter:
        def __init__(self, *_): ...
        async def hit(self, *_):
            raise _FakeTooMany(12)
        async def reset(self, *_): ...

    monkeypatch.setattr(auth_module, "LoginRateLimiter", _FakeLimiter)

    resp = await client.post("/auth/login", json={"email": "user@test.com", "senha": "x"})

    body = resp.json()
    assert resp.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in body["error"]


@pytest.mark.anyio
async def test_login_form_200_retorna_token(client: httpx.AsyncClient, overrides: Any, monkeypatch: pytest.MonkeyPatch):
    from app.api.v1.endpoints import auth as auth_module
    monkeypatch.setattr(auth_module, "create_access_token", lambda payload: "test-token")

    overrides.autenticar.return_value = SimpleNamespace(email="user@test.com", role=UserRole.USER)

    resp = await client.post(
        "/auth/login/form",
        data={"username": "user@test.com", "password": "x"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()["access_token"] == "test-token"


@pytest.mark.anyio
async def test_login_form_401_quando_credenciais_invalidas(client: httpx.AsyncClient, overrides: Any):
    overrides.autenticar.side_effect = CredenciaisInvalidasError()

    resp = await client.post(
        "/auth/login/form",
        data={"username": "user@test.com", "password": "wrong"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert resp.status_code == HTTPStatus.UNAUTHORIZED
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.anyio
async def test_desativar_204(client: httpx.AsyncClient, overrides: Any):
    overrides.desativar.return_value = None

    resp = await client.patch("/auth/users/1/desativar")
    assert resp.status_code == HTTPStatus.NO_CONTENT
    overrides.desativar.assert_awaited_once_with(1)


@pytest.mark.anyio
async def test_desativar_404_quando_user_nao_encontrado(client: httpx.AsyncClient, overrides: Any):
    overrides.desativar.side_effect = UserNaoEncontradoError()

    resp = await client.patch("/auth/users/999/desativar")

    assert resp.status_code == HTTPStatus.NOT_FOUND
    assert resp.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.anyio
async def test_atualizar_role_200(client: httpx.AsyncClient, overrides: Any):
    overrides.atualizar_role.return_value = SimpleNamespace(id=1, email="u@test.com", role=UserRole.ADMIN, ativo=True)

    resp = await client.patch("/auth/users/1/role", json={"role": "ADMIN"})

    body = resp.json()
    assert resp.status_code == HTTPStatus.OK
    assert body["id"] == 1
    assert body["role"] == "ADMIN"
    overrides.atualizar_role.assert_awaited_once()
    _, kwargs = overrides.atualizar_role.await_args
    assert kwargs["user_id"] == 1
    assert kwargs["nova_role"] == UserRole.ADMIN


@pytest.mark.anyio
async def test_atualizar_role_404_quando_user_nao_encontrado(client: httpx.AsyncClient, overrides: Any):
    overrides.atualizar_role.side_effect = UserNaoEncontradoError()

    resp = await client.patch("/auth/users/999/role", json={"role": "ADMIN"})

    assert resp.status_code == HTTPStatus.NOT_FOUND
    assert resp.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.anyio
async def test_register_400_quando_senha_invalida(client, app):
    # Arrange
    service = AsyncMock()
    service.criar.side_effect = SenhaInvalidaError("senha ruim")

    app.dependency_overrides[dep_get_user_service] = lambda: service

    payload = {"email": "user@test.com", "senha": "x", "role": "USER"}

    # Act
    resp = await client.post("/auth/register", json=payload)

    # Assert
    body = resp.json()
    assert resp.status_code == HTTPStatus.BAD_REQUEST
    assert body["error"]["code"] == ErrorCode.VALIDATION_ERROR
    assert "senha" in body["error"]["message"].lower()


@pytest.mark.anyio
async def test_register_400_quando_email_invalido(client, app):
    # Arrange
    service = AsyncMock()
    service.criar.side_effect = EmailInvalidoError("email ruim")

    app.dependency_overrides[dep_get_user_service] = lambda: service

    payload = {"email": "invalido", "senha": "Senha@123", "role": "USER"}

    # Act
    resp = await client.post("/auth/register", json=payload)

    # Assert
    body = resp.json()
    assert resp.status_code == HTTPStatus.BAD_REQUEST
    assert body["error"]["code"] == ErrorCode.VALIDATION_ERROR
    assert "email" in body["error"]["message"].lower()


@pytest.mark.anyio
async def test_login_form_429_quando_rate_limited(client, app, fake_redis, monkeypatch):
    import app.api.v1.endpoints.auth as auth_module
    import app.core.infra as infra_module

    app.dependency_overrides[infra_module.get_redis] = lambda: fake_redis

    async def _hit(*args, **kwargs):
        raise TooManyRequestsError(retry_after_seconds=42)

    monkeypatch.setattr(auth_module.LoginRateLimiter, "hit", _hit, raising=True)

    resp = await client.post(
        "/auth/login/form",
        data={"username": "user@test.com", "password": "wrong"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    body = resp.json()
    assert resp.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert body["error"]["code"] == ErrorCode.VALIDATION_ERROR
    assert "muitas tentativas" in body["error"]["message"].lower()
    assert body["error"].get("details", {}).get("retry_after_seconds") == 42
