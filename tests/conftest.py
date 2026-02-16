from __future__ import annotations

import os
import time
import pytest
import pytest_asyncio
import httpx

from dataclasses import replace
from decimal import Decimal
from typing import AsyncIterator, Dict, Optional, Any


def _set_test_env() -> None:
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/tinnova_test",
    )
    os.environ.setdefault(
        "DATABASE_URL_SYNC",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/tinnova_test",
    )
    os.environ.setdefault("JWT_SECRET", "test-secret")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

    os.environ.setdefault(
        "database_url",
        os.environ["DATABASE_URL"],
    )
    os.environ.setdefault(
        "database_url_sync",
        os.environ["DATABASE_URL_SYNC"],
    )
    os.environ.setdefault("jwt_secret", os.environ["JWT_SECRET"])
    os.environ.setdefault("redis_url", os.environ["REDIS_URL"])

    os.environ.setdefault("ENV", "test")


_set_test_env()


from app.core.enums.user_role import UserRole
from app.domain.user import User
from app.domain.veiculo import Veiculo
from app.services.user_service import UserService
from app.services.veiculo_service import VeiculoService
from app.services.fx.fx_provider import FxProvider
from app.exceptions.user_exceptions import UserNaoEncontradoError
from app.exceptions.veiculo_exceptions import VeiculoNaoEncontradoError
from app.api.deps import get_user_service as dep_get_user_service
from app.core.infra import get_redis as dep_get_redis
from app.services.fx.deps import get_fx_provider as dep_get_fx_provider


try:
    from app.api.v1.endpoints.veiculos import get_veiculo_service as dep_get_veiculo_service
except Exception:
    dep_get_veiculo_service = None

from main import app as fastapi_app


class FakeRedis:
    def __init__(self):
        self._store: Dict[bytes, bytes] = {}
        self._expire_at: Dict[bytes, float] = {}

    def _now(self) -> float:
        return time.time()

    def _purge_if_expired(self, key: bytes) -> None:
        exp = self._expire_at.get(key)
        if exp is not None and self._now() >= exp:
            self._store.pop(key, None)
            self._expire_at.pop(key, None)

    async def get(self, key: bytes) -> Optional[bytes]:
        self._purge_if_expired(key)
        return self._store.get(key)

    async def set(self, key: bytes, value: bytes, ex: Optional[int] = None) -> bool:
        self._store[key] = value
        if ex is not None:
            self._expire_at[key] = self._now() + ex
        return True

    async def delete(self, key: bytes) -> int:
        existed = 1 if key in self._store else 0
        self._store.pop(key, None)
        self._expire_at.pop(key, None)
        return existed

    async def incr(self, key: bytes) -> int:
        self._purge_if_expired(key)
        raw = self._store.get(key, b"0")
        n = int(raw.decode("utf-8")) + 1
        self._store[key] = str(n).encode("utf-8")
        return n

    async def expire(self, key: bytes, seconds: int) -> bool:
        self._purge_if_expired(key)
        if key not in self._store:
            return False
        self._expire_at[key] = self._now() + seconds
        return True

    async def ttl(self, key: bytes) -> int:
        self._purge_if_expired(key)
        if key not in self._store:
            return -2
        exp = self._expire_at.get(key)
        if exp is None:
            return -1
        remaining = int(exp - self._now())
        return max(0, remaining)

    async def aclose(self) -> None:
        return


class FakeFxProvider(FxProvider):
    def __init__(self, rate_brl_per_usd: Decimal = Decimal("5.00")):
        self.rate = rate_brl_per_usd

    async def brl_to_usd(self, brl: Decimal) -> Decimal:
        return (brl / self.rate).quantize(Decimal("0.01"))


class FakeUserRepository:
    def __init__(self):
        self._by_id: Dict[int, User] = {}
        self._by_email: Dict[str, User] = {}
        self._seq = 1

    async def get_by_id(self, user_id: int) -> Optional[User]:
        u = self._by_id.get(user_id)
        return u if u and u.ativo else None

    async def get_by_email(self, email: str) -> Optional[User]:
        u = self._by_email.get(email)
        return u if u and u.ativo else None

    async def add(self, entity: User) -> User:
        user = entity
        if user.id is None:
            user = replace(user, id=self._seq)
            self._seq += 1
        self._by_id[user.id] = user
        self._by_email[user.email] = user
        return user

    async def soft_delete(self, user_id: int) -> None:
        u = self._by_id.get(user_id)
        if not u:
            raise UserNaoEncontradoError()
        updated = replace(u, ativo=False)
        self._by_id[user_id] = updated
        self._by_email[u.email] = updated

    async def update_role(self, user_id: int, role: UserRole) -> User:
        u = self._by_id.get(user_id)
        if not u:
            raise UserNaoEncontradoError()
        updated = replace(u, role=role)
        self._by_id[user_id] = updated
        self._by_email[updated.email] = updated
        return updated


class FakeVeiculoRepository:
    def __init__(self):
        self._by_id: Dict[int, Veiculo] = {}
        self._by_placa: Dict[str, Veiculo] = {}
        self._seq = 1

    async def get_by_id(self, veiculo_id: int) -> Optional[Veiculo]:
        v = self._by_id.get(veiculo_id)
        return v if v and v.ativo else None

    async def get_by_placa(self, placa: str) -> Optional[Veiculo]:
        v = self._by_placa.get(placa)
        return v if v and v.ativo else None

    async def add(self, entity: Veiculo) -> Veiculo:
        v = entity
        if v.id is None:
            v = replace(v, id=self._seq)
            self._seq += 1
        self._by_id[v.id] = v
        self._by_placa[v.placa] = v
        return v

    async def update_fields(self, veiculo_id: int, fields: dict) -> Optional[Veiculo]:
        v = self._by_id.get(veiculo_id)
        if not v or not v.ativo:
            return None
        updated = replace(v, **fields)
        self._by_id[veiculo_id] = updated
        self._by_placa[updated.placa] = updated
        return updated

    async def soft_delete(self, veiculo_id: int) -> None:
        v = self._by_id.get(veiculo_id)
        if not v:
            raise VeiculoNaoEncontradoError()
        updated = replace(v, ativo=False)
        self._by_id[veiculo_id] = updated
        self._by_placa[v.placa] = updated

    async def list(self, **kwargs) -> tuple[list[Veiculo], int]:
        items = [v for v in self._by_id.values() if v.ativo]
        return items, len(items)

    async def relatorio_por_marca(self) -> list[tuple[str, int]]:
        counter: Dict[str, int] = {}
        for v in self._by_id.values():
            if v.ativo:
                counter[v.marca] = counter.get(v.marca, 0) + 1
        return sorted(counter.items(), key=lambda x: x[1], reverse=True)


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest_asyncio.fixture
async def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest_asyncio.fixture
async def fake_fx() -> FakeFxProvider:
    return FakeFxProvider(rate_brl_per_usd=Decimal("5.00"))


@pytest_asyncio.fixture
async def fake_user_repo() -> FakeUserRepository:
    return FakeUserRepository()


@pytest_asyncio.fixture
async def fake_veiculo_repo() -> FakeVeiculoRepository:
    return FakeVeiculoRepository()


@pytest_asyncio.fixture
async def user_service(fake_user_repo: FakeUserRepository) -> UserService:
    return UserService(fake_user_repo)


@pytest_asyncio.fixture
async def veiculo_service(
    fake_veiculo_repo: FakeVeiculoRepository,
    fake_fx: FakeFxProvider,
) -> VeiculoService:
    return VeiculoService(fake_veiculo_repo, fake_fx)


@pytest_asyncio.fixture
async def app(
    fake_redis: FakeRedis,
    fake_fx: FakeFxProvider,
    user_service: UserService,
    veiculo_service: VeiculoService,
) -> AsyncIterator[Any]:
    async def _override_get_redis():
        yield fake_redis

    async def _override_get_fx_provider():
        yield fake_fx

    def _override_get_user_service():
        return user_service

    def _override_get_veiculo_service():
        return veiculo_service

    fastapi_app.dependency_overrides[dep_get_redis] = _override_get_redis
    fastapi_app.dependency_overrides[dep_get_fx_provider] = _override_get_fx_provider
    fastapi_app.dependency_overrides[dep_get_user_service] = _override_get_user_service

    if dep_get_veiculo_service is not None:
        fastapi_app.dependency_overrides[dep_get_veiculo_service] = _override_get_veiculo_service

    yield fastapi_app

    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app: Any) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
