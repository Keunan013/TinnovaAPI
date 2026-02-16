from __future__ import annotations

import pytest

from http import HTTPStatus

import app.api.deps as deps_module

from app.core.enums.user_role import UserRole
from app.core.schemas.current_user import CurrentUser


@pytest.mark.anyio
async def test_get_current_user_quando_decode_token_retorna_none_deve_chamar_raise_api_error(monkeypatch: pytest.MonkeyPatch):
    # Arrange
    monkeypatch.setattr(deps_module, "decode_token", lambda _token: None)

    calls = []

    def fake_raise_api_error(status_code, code, message, details=None):
        calls.append((status_code, code, message, details))
        raise RuntimeError("api_error")

    monkeypatch.setattr(deps_module, "raise_api_error", fake_raise_api_error)

    # Act / Assert
    with pytest.raises(RuntimeError, match="api_error"):
        await deps_module.get_current_user(token="bad-token")

    status_code, code, message, details = calls[0]
    assert len(calls) == 1
    assert status_code == HTTPStatus.UNAUTHORIZED
    assert message == "Token inválido"
    assert details is None


@pytest.mark.anyio
async def test_get_current_user_quando_token_sem_sub_deve_401(monkeypatch: pytest.MonkeyPatch):
    # Arrange
    monkeypatch.setattr(deps_module, "decode_token", lambda _token: {"role": "ADMIN"})

    def fake_raise_api_error(*args, **kwargs):
        raise RuntimeError("api_error")

    monkeypatch.setattr(deps_module, "raise_api_error", fake_raise_api_error)

    # Act / Assert
    with pytest.raises(RuntimeError, match="api_error"):
        await deps_module.get_current_user(token="token")


@pytest.mark.anyio
async def test_get_current_user_quando_token_sem_role_deve_401(monkeypatch: pytest.MonkeyPatch):
    # Arrange
    monkeypatch.setattr(deps_module, "decode_token", lambda _token: {"sub": "a@b.com"})

    def fake_raise_api_error(*args, **kwargs):
        raise RuntimeError("api_error")

    monkeypatch.setattr(deps_module, "raise_api_error", fake_raise_api_error)

    # Act / Assert
    with pytest.raises(RuntimeError, match="api_error"):
        await deps_module.get_current_user(token="token")


@pytest.mark.anyio
async def test_get_current_user_quando_token_ok_deve_retornar_CurrentUser(monkeypatch: pytest.MonkeyPatch):
    # Arrange
    monkeypatch.setattr(
        deps_module,
        "decode_token",
        lambda _token: {"sub": "user@test.com", "role": "ADMIN"},
    )

    monkeypatch.setattr(deps_module, "raise_api_error", lambda *a, **k: (_ for _ in ()).throw(AssertionError))

    # Act
    out = await deps_module.get_current_user(token="good")

    # Assert
    assert isinstance(out, CurrentUser)
    assert out.email == "user@test.com"
    assert out.role == "ADMIN"


@pytest.mark.anyio
async def test_require_admin_quando_role_nao_admin_deve_403(monkeypatch: pytest.MonkeyPatch):
    # Arrange
    calls = []

    def fake_raise_api_error(status_code, code, message, details=None):
        calls.append((status_code, code, message, details))
        raise RuntimeError("api_error")

    monkeypatch.setattr(deps_module, "raise_api_error", fake_raise_api_error)

    user = CurrentUser(email="x@y.com", role=UserRole.USER)

    # Act / Assert
    with pytest.raises(RuntimeError, match="api_error"):
        await deps_module.require_admin(user=user)

    status_code, code, message, details = calls[0]
    assert len(calls) == 1
    assert status_code == HTTPStatus.FORBIDDEN
    assert message == "Acesso negado"
    assert details is None


@pytest.mark.anyio
async def test_require_admin_quando_admin_deve_retornar_user(monkeypatch: pytest.MonkeyPatch):
    # Arrange
    monkeypatch.setattr(deps_module, "raise_api_error", lambda *a, **k: (_ for _ in ()).throw(AssertionError))

    user = CurrentUser(email="admin@test.com", role=UserRole.ADMIN)

    # Act
    out = await deps_module.require_admin(user=user)

    # Assert
    assert user == out
