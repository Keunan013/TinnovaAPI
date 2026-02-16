from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.core.enums.user_role import UserRole
from app.core.enums.error_code import ErrorCode
from app.core.http_errors import raise_api_error
from app.core.schemas.current_user import CurrentUser
from app.core.database import get_db
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService


# Swagger password-flow (form)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login/form")


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(UserRepository(db))


async def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    payload = decode_token(token)
    if not payload:
        raise_api_error(
            status.HTTP_401_UNAUTHORIZED,
            ErrorCode.UNAUTHORIZED,
            "Token inválido",
        )

    email = payload.get("sub")
    role = payload.get("role")
    if not email or not role:
        raise_api_error(
            status.HTTP_401_UNAUTHORIZED,
            ErrorCode.UNAUTHORIZED,
            "Token inválido",
        )

    return CurrentUser(
        email=email,
        role=role,
    )


async def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role != UserRole.ADMIN:
        raise_api_error(
            status.HTTP_403_FORBIDDEN,
            ErrorCode.FORBIDDEN,
            "Acesso negado",
        )
    return user
