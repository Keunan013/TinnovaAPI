from app.core.enums.user_role import UserRole
from app.core.security import hash_password, verify_password
from app.domain.user import User
from app.domain.validators.password_validator import PasswordValidator
from app.domain.validators.email_validator import StrongEmailValidator
from app.repositories.user_repository import UserRepository
from app.exceptions.user_exceptions import (
    EmailDuplicadoError,
    UserNaoEncontradoError,
    CredenciaisInvalidasError,
)
from sqlalchemy.exc import IntegrityError


class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def obter_por_id(self, user_id: int) -> User:
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise UserNaoEncontradoError()
        return user

    async def obter_por_email(self, email: str) -> User:
        email = (email or "").strip().lower()
        user = await self.repository.get_by_email(email)
        if not user:
            raise UserNaoEncontradoError()
        return user

    async def criar(
        self,
        *,
        email: str,
        senha: str,
        role: UserRole = UserRole.USER,
    ) -> User:
        normalized = StrongEmailValidator.validate_and_normalize(email)

        existente = await self.repository.get_by_email(normalized.value)
        if existente:
            raise EmailDuplicadoError()

        PasswordValidator.validate(senha)

        entity = User(
            id=None,
            email=normalized.value,
            senha_hash=hash_password(senha),
            role=role,
            ativo=True,
        )
        try:
            return await self.repository.add(entity)
        except IntegrityError:
            raise EmailDuplicadoError()

    async def autenticar(self, email: str, senha: str) -> User:
        email = (email or "").strip().lower()
        user = await self.repository.get_by_email(email)
        if not user:
            raise CredenciaisInvalidasError()
        if not verify_password(senha, user.senha_hash):
            raise CredenciaisInvalidasError()
        return user

    async def atualizar_role(
        self,
        user_id: int,
        nova_role: UserRole,
    ) -> User:

        user = await self.repository.get_by_id(user_id)
        if not user:
            raise UserNaoEncontradoError()

        if user.role == nova_role:
            return user

        atualizado = await self.repository.update_fields(
            user_id,
            {"role": nova_role.value},
        )

        if not atualizado:
            raise UserNaoEncontradoError()

        return atualizado

    # Soft delete
    async def desativar(self, user_id: int) -> None:
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise UserNaoEncontradoError()
        await self.repository.soft_delete(user_id)
