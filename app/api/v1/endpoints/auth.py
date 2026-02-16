from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.infra import get_redis
from app.core.security import create_access_token
from app.core.enums.error_code import ErrorCode
from app.core.http_errors import raise_api_error
from app.mappers.user_mapper import to_dto
from app.security.rate_limiter import LoginRateLimiter, RateLimitKey, TooManyRequestsError
from app.services.user_service import UserService
from app.api.deps import require_admin, get_user_service
from app.schemas.register_request import RegisterRequest
from app.schemas.token_response import TokenResponse
from app.schemas.user_public import UserPublic
from app.schemas.update_role_request import UpdateRoleRequest
from app.schemas.login_request import LoginRequest
from app.domain.validators.password_validator import SenhaInvalidaError
from app.domain.validators.email_validator import EmailInvalidoError
from app.exceptions.user_exceptions import (
    CredenciaisInvalidasError,
    EmailDuplicadoError,
    UserNaoEncontradoError,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


async def _check_rate_limit(limiter: LoginRateLimiter, key: RateLimitKey) -> None:
    try:
        await limiter.hit(key)
    except TooManyRequestsError as e:
        raise_api_error(
            status.HTTP_429_TOO_MANY_REQUESTS,
            ErrorCode.VALIDATION_ERROR,
            "Muitas tentativas. Tente novamente mais tarde.",
            details={"retry_after_seconds": e.retry_after_seconds},
        )


async def _authenticate_and_issue_token(
    *,
    service: UserService,
    limiter: LoginRateLimiter,
    key: RateLimitKey,
    email_norm: str,
    password: str,
) -> TokenResponse:
    try:
        user = await service.autenticar(email_norm, password)
    except CredenciaisInvalidasError:
        raise_api_error(
            status.HTTP_401_UNAUTHORIZED,
            ErrorCode.UNAUTHORIZED,
            "Credenciais inválidas",
        )

    await limiter.reset(key)

    token = create_access_token({"sub": user.email, "role": user.role.value})
    return TokenResponse(access_token=token)


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserPublic)
async def register(
    payload: RegisterRequest,
    service: UserService = Depends(get_user_service),
) -> UserPublic:
    try:
        user = await service.criar(email=payload.email, senha=payload.senha, role=payload.role)
        return to_dto(user)

    except EmailDuplicadoError:
        raise_api_error(status.HTTP_409_CONFLICT, ErrorCode.VALIDATION_ERROR, "Email já cadastrado")

    except (SenhaInvalidaError, EmailInvalidoError) as e:
        raise_api_error(status.HTTP_400_BAD_REQUEST, ErrorCode.VALIDATION_ERROR, str(e))


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    payload: LoginRequest,
    redis_client=Depends(get_redis),
    service: UserService = Depends(get_user_service),
) -> TokenResponse:
    ip = _client_ip(request)
    email_norm = payload.email
    limiter = LoginRateLimiter(redis_client)
    key = RateLimitKey(ip=ip, username=email_norm)

    await _check_rate_limit(limiter, key)

    return await _authenticate_and_issue_token(
        service=service,
        limiter=limiter,
        key=key,
        email_norm=email_norm,
        password=payload.senha,
    )


@router.post("/login/form", include_in_schema=False, response_model=TokenResponse)
async def login_form(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    redis_client=Depends(get_redis),
    service: UserService = Depends(get_user_service),
) -> TokenResponse:
    ip = _client_ip(request)
    email_norm = form_data.username
    limiter = LoginRateLimiter(redis_client)
    key = RateLimitKey(ip=ip, username=email_norm)

    await _check_rate_limit(limiter, key)

    return await _authenticate_and_issue_token(
        service=service,
        limiter=limiter,
        key=key,
        email_norm=email_norm,
        password=form_data.password,
    )


# Soft delete
@router.patch("/users/{user_id}/desativar", status_code=status.HTTP_204_NO_CONTENT)
async def desativar_usuario(
    user_id: int,
    _admin=Depends(require_admin),
    service: UserService = Depends(get_user_service),
) -> None:
    try:
        await service.desativar(user_id)
    except UserNaoEncontradoError:
        raise_api_error(status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND, "Usuário não encontrado")
    return None


@router.patch("/users/{user_id}/role", response_model=UserPublic)
async def atualizar_role_usuario(
    user_id: int,
    payload: UpdateRoleRequest,
    _admin=Depends(require_admin),
    service: UserService = Depends(get_user_service),
) -> UserPublic:
    try:
        user = await service.atualizar_role(user_id=user_id, nova_role=payload.role)
        return to_dto(user)
    except UserNaoEncontradoError:
        raise_api_error(status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND, "Usuário não encontrado")
