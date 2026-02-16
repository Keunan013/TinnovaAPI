from __future__ import annotations

import pytest

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, List, Optional
from unittest.mock import AsyncMock, MagicMock

from app.core.enums.user_role import UserRole
from app.domain.user import User
from app.repositories.user_repository import UserRepository


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
def repo(session_mock: MagicMock) -> UserRepository:
    return UserRepository(session_mock)


@pytest.mark.asyncio
async def test_get_by_id_returns_domain(repo: UserRepository, session_mock: MagicMock, monkeypatch):
    import app.repositories.user_repository as repo_module

    fake_model = SimpleNamespace(
        id=1,
        email="user@test.com",
        senha_hash="hash",
        role="USER",
        ativo=True,
        created_at=None,
        updated_at=None,
    )

    expected = User(
        id=1,
        email="user@test.com",
        senha_hash="hash",
        role=UserRole.USER,
        ativo=True,
    )

    session_mock.execute.return_value = _ExecuteResult(scalar_one_or_none=fake_model)
    monkeypatch.setattr(repo_module, "to_domain", lambda m: expected)

    got = await repo.get_by_id(1)
    assert expected == got


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_not_found(repo: UserRepository, session_mock: MagicMock):
    session_mock.execute.return_value = _ExecuteResult(scalar_one_or_none=None)
    got = await repo.get_by_id(999)
    assert got is None


@pytest.mark.asyncio
async def test_get_by_email_returns_domain(repo: UserRepository, session_mock: MagicMock, monkeypatch):
    import app.repositories.user_repository as repo_module

    fake_model = SimpleNamespace(
        id=2,
        email="admin@test.com",
        senha_hash="hash2",
        role="ADMIN",
        ativo=True,
        created_at=None,
        updated_at=None,
    )

    expected = User(
        id=2,
        email="admin@test.com",
        senha_hash="hash2",
        role=UserRole.ADMIN,
        ativo=True,
    )

    session_mock.execute.return_value = _ExecuteResult(scalar_one_or_none=fake_model)
    monkeypatch.setattr(repo_module, "to_domain", lambda m: expected)

    got = await repo.get_by_email("admin@test.com")
    assert expected == got


@pytest.mark.asyncio
async def test_get_by_email_returns_none_when_not_found(repo: UserRepository, session_mock: MagicMock):
    session_mock.execute.return_value = _ExecuteResult(scalar_one_or_none=None)
    got = await repo.get_by_email("missing@test.com")
    assert got is None


@pytest.mark.asyncio
async def test_update_fields_commits_and_returns_updated(repo: UserRepository, session_mock: MagicMock, monkeypatch):
    import app.repositories.user_repository as repo_module

    # update_fields chama:
    # 1) session.execute(update...)
    # 2) session.commit()
    # 3) get_by_id -> session.execute(select...) e mapper
    fake_model = SimpleNamespace(
        id=10,
        email="user10@test.com",
        senha_hash="hash10",
        role="ADMIN",
        ativo=True,
        created_at=None,
        updated_at=None,
    )

    session_mock.execute.side_effect = [
        _ExecuteResult(),  # update
        _ExecuteResult(scalar_one_or_none=fake_model),  # select do get_by_id
    ]

    expected = User(
        id=10,
        email="user10@test.com",
        senha_hash="hash10",
        role=UserRole.ADMIN,
        ativo=True,
    )
    monkeypatch.setattr(repo_module, "to_domain", lambda m: expected)

    got = await repo.update_fields(10, {"role": "ADMIN"})
    session_mock.commit.assert_awaited_once()
    assert got == expected
    assert session_mock.execute.await_count == 2


@pytest.mark.asyncio
async def test_soft_delete_commits(repo: UserRepository, session_mock: MagicMock):
    session_mock.execute.return_value = _ExecuteResult()
    await repo.soft_delete(10)
    session_mock.commit.assert_awaited_once()
    session_mock.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_commits_refreshes_and_returns_domain(repo: UserRepository, session_mock: MagicMock, monkeypatch):
    import app.repositories.user_repository as repo_module

    added_models: list[Any] = []

    def _add_side_effect(model: Any):
        added_models.append(model)

    async def _refresh_side_effect(model: Any):
        setattr(model, "id", 1)

    session_mock.add.side_effect = _add_side_effect
    session_mock.commit.return_value = None
    session_mock.refresh.side_effect = _refresh_side_effect

    expected = User(
        id=1,
        email="new@test.com",
        senha_hash="hash-new",
        role=UserRole.USER,
        ativo=True,
    )
    monkeypatch.setattr(repo_module, "to_domain", lambda m: expected)

    entity = User(
        id=None,
        email="new@test.com",
        senha_hash="hash-new",
        role=UserRole.USER,
        ativo=True,
    )

    got = await repo.add(entity)

    session_mock.add.assert_called_once()
    session_mock.commit.assert_awaited_once()
    session_mock.refresh.assert_awaited_once()
    assert got == expected
    assert "Esperava capturar o model adicionado", added_models
    assert 1 == getattr(added_models[0], "id", None)


@pytest.mark.asyncio
async def test_add_rolls_back_on_integrity_error(repo: UserRepository, session_mock: MagicMock):
    from sqlalchemy.exc import IntegrityError

    session_mock.commit.side_effect = IntegrityError("stmt", "params", "orig")

    entity = User(
        id=None,
        email="dup@test.com",
        senha_hash="hash",
        role=UserRole.USER,
        ativo=True,
    )

    with pytest.raises(IntegrityError):
        await repo.add(entity)

    session_mock.rollback.assert_awaited_once()
