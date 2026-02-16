from __future__ import annotations

import pytest

from dataclasses import replace
from typing import Optional, Dict, Any

from app.core.enums.user_role import UserRole
from app.domain.user import User
from app.services.user_service import UserService
from app.exceptions.user_exceptions import (
    EmailDuplicadoError,
    UserNaoEncontradoError,
    CredenciaisInvalidasError,
)


class _EmailNormalized:
    def __init__(self, value: str):
        self.value = value


class FakeUserRepository:
    def __init__(self):
        self._by_id: Dict[int, User] = {}
        self._by_email: Dict[str, User] = {}
        self._seq = 1
        self.update_fields_calls: list[tuple[int, Dict[str, Any]]] = []

    async def get_by_id(self, user_id: int) -> Optional[User]:
        u = self._by_id.get(user_id)
        return u if u and u.ativo else None

    async def get_by_email(self, email: str) -> Optional[User]:
        u = self._by_email.get(email)
        return u if u and u.ativo else None

    async def add(self, entity: User) -> User:
        u = entity
        if u.id is None:
            u = replace(u, id=self._seq)
            self._seq += 1
        self._by_id[u.id] = u
        self._by_email[u.email] = u
        return u

    async def update_fields(self, user_id: int, fields: dict) -> Optional[User]:
        self.update_fields_calls.append((user_id, dict(fields)))

        u = self._by_id.get(user_id)
        if not u or not u.ativo:
            return None

        # services envia {"role": nova_role.value} => converte para UserRole
        if "role" in fields and isinstance(fields["role"], str):
            fields = dict(fields)
            fields["role"] = UserRole(fields["role"])

        updated = replace(u, **fields)
        self._by_id[user_id] = updated
        self._by_email[updated.email] = updated
        return updated

    async def soft_delete(self, user_id: int) -> None:
        u = self._by_id.get(user_id)
        if not u:
            raise UserNaoEncontradoError()
        updated = replace(u, ativo=False)
        self._by_id[user_id] = updated
        self._by_email[u.email] = updated


@pytest.fixture
def repo() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture
def service(repo: FakeUserRepository) -> UserService:
    return UserService(repo)  # type: ignore[arg-type]


@pytest.mark.anyio
async def test_obter_por_id_quando_existe_deve_retornar_usuario(
    service: UserService,
    repo: FakeUserRepository,
):
    # Arrange
    created = await repo.add(
        User(
            id=None,
            email="user@test.com",
            senha_hash="hash",
            role=UserRole.USER,
            ativo=True,
        )
    )

    # Act
    got = await service.obter_por_id(created.id)

    # Assert
    assert got.id == created.id
    assert got.email == "user@test.com"
    assert got.role == UserRole.USER
    assert got.ativo is True


@pytest.mark.anyio
async def test_obter_por_id_quando_nao_existe_deve_levantar_user_nao_encontrado(service: UserService):
    # Arrange
    # Act / Assert
    with pytest.raises(UserNaoEncontradoError):
        await service.obter_por_id(123)


@pytest.mark.anyio
async def test_obter_por_email_normaliza_e_quando_nao_existe_deve_levantar_user_nao_encontrado(service: UserService):
    with pytest.raises(UserNaoEncontradoError):
        await service.obter_por_email("  X@Y.com  ")


@pytest.mark.anyio
async def test_criar_quando_email_duplicado_deve_levantar_email_duplicado(
    service: UserService,
    repo: FakeUserRepository,
    monkeypatch: pytest.MonkeyPatch,
):
    # Arrange
    existing = User(
        id=1,
        email="user@test.com",
        senha_hash="hash",
        role=UserRole.USER,
        ativo=True,
    )
    await repo.add(existing)

    # Normalizador retorna exatamente o email duplicado
    from app.services import user_service as user_service_module

    monkeypatch.setattr(
        user_service_module.StrongEmailValidator,
        "validate_and_normalize",
        staticmethod(lambda _: _EmailNormalized("user@test.com")),
    )
    monkeypatch.setattr(
        user_service_module.PasswordValidator,
        "validate",
        staticmethod(lambda _: None),
    )
    monkeypatch.setattr(user_service_module, "hash_password", lambda _: "hashed")

    # Act / Assert
    with pytest.raises(EmailDuplicadoError):
        await service.criar(email="USER@TEST.COM", senha="x", role=UserRole.USER)


@pytest.mark.anyio
async def test_criar_quando_sucesso_deve_salvar_email_normalizado_e_role(
    service: UserService,
    repo: FakeUserRepository,
    monkeypatch: pytest.MonkeyPatch,
):
    # Arrange
    from app.services import user_service as user_service_module

    monkeypatch.setattr(
        user_service_module.StrongEmailValidator,
        "validate_and_normalize",
        staticmethod(lambda _: _EmailNormalized("normalized@test.com")),
    )
    monkeypatch.setattr(
        user_service_module.PasswordValidator,
        "validate",
        staticmethod(lambda _: None),
    )
    monkeypatch.setattr(user_service_module, "hash_password", lambda _: "hashed-pass")

    # Act
    created = await service.criar(email=" ANY@THING.COM ", senha="Senha@123", role=UserRole.ADMIN)

    # Assert
    assert created.id is not None
    assert created.email == "normalized@test.com"
    assert created.senha_hash == "hashed-pass"
    assert created.role == UserRole.ADMIN
    assert created.ativo is True
    loaded = await repo.get_by_email("normalized@test.com")
    assert loaded is not None
    assert loaded.id == created.id


@pytest.mark.anyio
async def test_autenticar_quando_email_nao_existe_deve_levantar_credenciais_invalidas(service: UserService):
    with pytest.raises(CredenciaisInvalidasError):
        await service.autenticar("nope@test.com", "x")


@pytest.mark.anyio
async def test_autenticar_quando_senha_incorreta_deve_levantar_credenciais_invalidas(
    service: UserService,
    repo: FakeUserRepository,
    monkeypatch: pytest.MonkeyPatch,
):
    # Arrange
    await repo.add(
        User(
            id=None,
            email="user@test.com",
            senha_hash="hash",
            role=UserRole.USER,
            ativo=True,
        )
    )

    from app.services import user_service as user_service_module
    monkeypatch.setattr(user_service_module, "verify_password", lambda *_: False)

    # Act / Assert
    with pytest.raises(CredenciaisInvalidasError):
        await service.autenticar(" user@test.com ", "wrong")


@pytest.mark.anyio
async def test_autenticar_quando_ok_deve_retornar_usuario(
    service: UserService,
    repo: FakeUserRepository,
    monkeypatch: pytest.MonkeyPatch,
):
    # Arrange
    await repo.add(
        User(
            id=None,
            email="user@test.com",
            senha_hash="hash",
            role=UserRole.USER,
            ativo=True,
        )
    )

    from app.services import user_service as user_service_module
    monkeypatch.setattr(user_service_module, "verify_password", lambda *_: True)

    # Act
    u = await service.autenticar(" USER@test.com ", "ok")

    # Assert
    assert u.email == "user@test.com"
    assert u.role == UserRole.USER
    assert u.ativo is True


@pytest.mark.anyio
async def test_atualizar_role_quando_user_nao_existe_deve_levantar_user_nao_encontrado(service: UserService):
    with pytest.raises(UserNaoEncontradoError):
        await service.atualizar_role(user_id=999, nova_role=UserRole.ADMIN)


@pytest.mark.anyio
async def test_atualizar_role_quando_mesma_role_deve_retornar_sem_update_fields(
    service: UserService,
    repo: FakeUserRepository,
):
    # Arrange
    u = await repo.add(
        User(
            id=None,
            email="user@test.com",
            senha_hash="hash",
            role=UserRole.USER,
            ativo=True,
        )
    )

    # Act
    out = await service.atualizar_role(user_id=u.id, nova_role=UserRole.USER)

    # Assert
    assert out.role == UserRole.USER
    assert repo.update_fields_calls == []


@pytest.mark.anyio
async def test_atualizar_role_quando_muda_role_deve_chamar_update_fields_com_value_e_retornar_atualizado(
    service: UserService,
    repo: FakeUserRepository,
):
    # Arrange
    u = await repo.add(
        User(
            id=None,
            email="user@test.com",
            senha_hash="hash",
            role=UserRole.USER,
            ativo=True,
        )
    )

    # Act
    out = await service.atualizar_role(user_id=u.id, nova_role=UserRole.ADMIN)

    # Assert
    assert repo.update_fields_calls == [(u.id, {"role": UserRole.ADMIN.value})]
    assert out.role == UserRole.ADMIN
    loaded = await repo.get_by_id(u.id)
    assert loaded is not None
    assert loaded.role == UserRole.ADMIN


@pytest.mark.anyio
async def test_desativar_quando_user_nao_existe_deve_levantar_user_nao_encontrado(service: UserService):
    with pytest.raises(UserNaoEncontradoError):
        await service.desativar(1)


@pytest.mark.anyio
async def test_desativar_quando_ok_deve_marcar_inativo(
    service: UserService,
    repo: FakeUserRepository,
):
    # Arrange
    u = await repo.add(
        User(
            id=None,
            email="user@test.com",
            senha_hash="hash",
            role=UserRole.USER,
            ativo=True,
        )
    )

    # Act
    await service.desativar(u.id)

    # Assert
    assert await repo.get_by_id(u.id) is None  # repo esconde inativo
    assert await repo.get_by_email(u.email) is None


@pytest.mark.anyio
async def test_obter_por_email_quando_existe_deve_retornar_usuario_normalizado(
    service: UserService,
    repo: FakeUserRepository,
):
    # Arrange
    await repo.add(
        User(
            id=None,
            email="user@test.com",
            senha_hash="hash",
            role=UserRole.USER,
            ativo=True,
        )
    )

    # Act
    got = await service.obter_por_email("  USER@TEST.COM  ")

    # Assert
    assert got.email == "user@test.com"
    assert got.ativo is True


@pytest.mark.anyio
async def test_criar_quando_integrity_error_no_repo_deve_levantar_email_duplicado(
    service: UserService,
    repo: FakeUserRepository,
    monkeypatch: pytest.MonkeyPatch,
):
    # Arrange: força validações
    from app.services import user_service as user_service_module

    monkeypatch.setattr(
        user_service_module.StrongEmailValidator,
        "validate_and_normalize",
        staticmethod(lambda _: _EmailNormalized("dup@test.com")),
    )
    monkeypatch.setattr(
        user_service_module.PasswordValidator,
        "validate",
        staticmethod(lambda _: None),
    )
    monkeypatch.setattr(user_service_module, "hash_password", lambda _: "hashed-pass")

    # força o repo.add a lançar IntegrityError
    from sqlalchemy.exc import IntegrityError

    async def _raise_integrity(_entity: User):
        raise IntegrityError("stmt", "params", "orig")

    monkeypatch.setattr(repo, "add", _raise_integrity)

    # Act / Assert
    with pytest.raises(EmailDuplicadoError):
        await service.criar(email="dup@test.com", senha="Senha@123", role=UserRole.USER)


@pytest.mark.anyio
async def test_atualizar_role_quando_update_fields_retorna_none_deve_levantar_user_nao_encontrado(
    service: UserService,
    repo: FakeUserRepository,
    monkeypatch: pytest.MonkeyPatch,
):
    # Arrange: existe usuário (passa do primeiro get_by_id)
    u = await repo.add(
        User(
            id=None,
            email="user@test.com",
            senha_hash="hash",
            role=UserRole.USER,
            ativo=True,
        )
    )

    async def _return_none(_user_id: int, _fields: dict):
        return None

    monkeypatch.setattr(repo, "update_fields", _return_none)

    # Act / Assert
    with pytest.raises(UserNaoEncontradoError):
        await service.atualizar_role(user_id=u.id, nova_role=UserRole.ADMIN)
