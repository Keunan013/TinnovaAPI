from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

from decimal import Decimal
from http import HTTPStatus
from types import SimpleNamespace
from typing import Any, AsyncIterator
from unittest.mock import AsyncMock

from app.core.database import get_db
from app.core.infra import get_redis
from app.services.fx.deps import get_fx_provider
from app.core.schemas.health_checks import HealthStatus


@pytest_asyncio.fixture
async def app() -> Any:
    from main import app as fastapi_app
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app: Any) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _assert_payload(resp_json: dict[str, Any], expected_status: HealthStatus, *, db: HealthStatus, redis: HealthStatus, fx: HealthStatus) -> None:
    assert resp_json["status"] == expected_status
    assert resp_json["checks"]["database"] == db
    assert resp_json["checks"]["redis"] == redis
    assert resp_json["checks"]["fx_provider"] == fx


@pytest.mark.anyio
async def test_health_ready_200_quando_tudo_ok(app: Any, client: httpx.AsyncClient):
    db = AsyncMock()
    db.execute = AsyncMock(return_value=None)

    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)

    fx = AsyncMock()
    fx.usd_brl_rate = AsyncMock(return_value=SimpleNamespace(usd_brl=Decimal("5.00")))

    async def _override_db():
        yield db

    async def _override_redis():
        yield redis

    async def _override_fx():
        yield fx

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_fx_provider] = _override_fx

    resp = await client.get("/health/ready")
    assert resp.status_code == HTTPStatus.OK

    body = resp.json()
    _assert_payload(
        body,
        HealthStatus.OK,
        db=HealthStatus.OK,
        redis=HealthStatus.OK,
        fx=HealthStatus.OK,
    )


@pytest.mark.anyio
async def test_health_ready_deve_retornar_degraded_quando_db_falha(app: Any, client: httpx.AsyncClient):
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=Exception("db down"))

    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)

    fx = AsyncMock()
    fx.usd_brl_rate = AsyncMock(return_value=SimpleNamespace(usd_brl=Decimal("5.00")))

    async def _override_db():
        yield db

    async def _override_redis():
        yield redis

    async def _override_fx():
        yield fx

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_fx_provider] = _override_fx

    resp = await client.get("/health/ready")
    assert resp.status_code == HTTPStatus.OK

    body = resp.json()
    _assert_payload(
        body,
        HealthStatus.DEGRADED,
        db=HealthStatus.ERROR,
        redis=HealthStatus.OK,
        fx=HealthStatus.OK,
    )


@pytest.mark.anyio
async def test_health_ready_deve_retornar_degraded_quando_redis_falha(app: Any, client: httpx.AsyncClient):
    db = AsyncMock()
    db.execute = AsyncMock(return_value=None)

    redis = AsyncMock()
    redis.ping = AsyncMock(side_effect=Exception("redis down"))

    fx = AsyncMock()
    fx.usd_brl_rate = AsyncMock(return_value=SimpleNamespace(usd_brl=Decimal("5.00")))

    async def _override_db():
        yield db

    async def _override_redis():
        yield redis

    async def _override_fx():
        yield fx

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_fx_provider] = _override_fx

    resp = await client.get("/health/ready")
    assert resp.status_code == HTTPStatus.OK

    body = resp.json()
    _assert_payload(
        body,
        HealthStatus.DEGRADED,
        db=HealthStatus.OK,
        redis=HealthStatus.ERROR,
        fx=HealthStatus.OK,
    )


@pytest.mark.anyio
async def test_health_ready_deve_retornar_degraded_quando_fx_rate_invalida(app: Any, client: httpx.AsyncClient):
    db = AsyncMock()
    db.execute = AsyncMock(return_value=None)

    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)

    fx = AsyncMock()
    # rate <= 0 => error
    fx.usd_brl_rate = AsyncMock(return_value=SimpleNamespace(usd_brl=Decimal("0")))

    async def _override_db():
        yield db

    async def _override_redis():
        yield redis

    async def _override_fx():
        yield fx

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_fx_provider] = _override_fx

    resp = await client.get("/health/ready")
    assert resp.status_code == HTTPStatus.OK

    body = resp.json()
    _assert_payload(
        body,
        HealthStatus.DEGRADED,
        db=HealthStatus.OK,
        redis=HealthStatus.OK,
        fx=HealthStatus.ERROR,
    )


@pytest.mark.anyio
async def test_health_ready_deve_retornar_degraded_quando_fx_explode(app: Any, client: httpx.AsyncClient):
    db = AsyncMock()
    db.execute = AsyncMock(return_value=None)

    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)

    fx = AsyncMock()
    fx.usd_brl_rate = AsyncMock(side_effect=Exception("fx down"))

    async def _override_db():
        yield db

    async def _override_redis():
        yield redis

    async def _override_fx():
        yield fx

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_fx_provider] = _override_fx

    resp = await client.get("/health/ready")
    assert resp.status_code == HTTPStatus.OK

    body = resp.json()
    _assert_payload(
        body,
        HealthStatus.DEGRADED,
        db=HealthStatus.OK,
        redis=HealthStatus.OK,
        fx=HealthStatus.ERROR,
    )
