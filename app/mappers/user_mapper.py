from app.domain.user import User
from app.models.user_model import UserModel
from app.core.enums.user_role import UserRole
from app.schemas.user_public import UserPublic


def to_domain(model: UserModel) -> User:
    return User(
        id=model.id,
        email=model.email,
        senha_hash=model.senha_hash,
        role=UserRole(model.role),
        ativo=model.ativo,
    )


def to_model(domain: User) -> UserModel:
    return UserModel(
        id=domain.id,
        email=domain.email,
        senha_hash=domain.senha_hash,
        role=domain.role.value,
        ativo=domain.ativo,
    )


def to_dto(domain: User) -> UserPublic:
    return UserPublic(
        id=domain.id,
        email=domain.email,
        role=domain.role,
        ativo=domain.ativo
    )
