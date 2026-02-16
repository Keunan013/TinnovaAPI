from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.enums.error_code import ErrorCode
from app.core.http_errors import api_error_payload
from app.domain.validators.password_validator import SenhaInvalidaError
from app.domain.validators.email_validator import EmailInvalidoError
from app.services.fx.fx_provider import FxRateUnavailableError
from app.exceptions.veiculo_exceptions import (
    PlacaDuplicadaError,
    VeiculoNaoEncontradoError,
    InvalidUpdateError,
)
from app.exceptions.user_exceptions import (
    EmailDuplicadoError,
    UserNaoEncontradoError,
    CredenciaisInvalidasError,
)


def _json_error(
    status_code: HTTPStatus,
    code: ErrorCode,
    message: str,
    details=None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code.value,
        content=api_error_payload(code, message, details),
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(PlacaDuplicadaError)
    async def placa_duplicada_handler(request: Request, exc: PlacaDuplicadaError):
        return _json_error(
            HTTPStatus.CONFLICT,
            ErrorCode.PLACA_DUPLICADA,
            "Placa já cadastrada",
        )

    @app.exception_handler(VeiculoNaoEncontradoError)
    async def veiculo_not_found_handler(request: Request, exc: VeiculoNaoEncontradoError):
        return _json_error(
            HTTPStatus.NOT_FOUND,
            ErrorCode.NOT_FOUND,
            "Veículo não encontrado",
        )

    @app.exception_handler(InvalidUpdateError)
    async def invalid_update_handler(request: Request, exc: InvalidUpdateError):
        return _json_error(
            HTTPStatus.BAD_REQUEST,
            ErrorCode.INVALID_UPDATE,
            exc.message,
        )

    @app.exception_handler(FxRateUnavailableError)
    async def fx_unavailable_handler(request: Request, exc: FxRateUnavailableError):
        return _json_error(
            HTTPStatus.SERVICE_UNAVAILABLE,
            ErrorCode.FX_UNAVAILABLE,
            "Não foi possível obter cotação USD-BRL",
        )

    @app.exception_handler(EmailDuplicadoError)
    async def email_duplicado_handler(request: Request, exc: EmailDuplicadoError):
        return _json_error(
            HTTPStatus.CONFLICT,
            ErrorCode.VALIDATION_ERROR,
            "Email já cadastrado",
        )

    @app.exception_handler(UserNaoEncontradoError)
    async def user_not_found_handler(request: Request, exc: UserNaoEncontradoError):
        return _json_error(
            HTTPStatus.NOT_FOUND,
            ErrorCode.NOT_FOUND,
            "Usuário não encontrado",
        )

    @app.exception_handler(CredenciaisInvalidasError)
    async def credenciais_invalidas_handler(request: Request, exc: CredenciaisInvalidasError):
        return _json_error(
            HTTPStatus.UNAUTHORIZED,
            ErrorCode.UNAUTHORIZED,
            "Credenciais inválidas",
        )

    @app.exception_handler(SenhaInvalidaError)
    async def senha_invalida_handler(request: Request, exc: SenhaInvalidaError):
        return _json_error(
            HTTPStatus.BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
            str(exc),
        )

    @app.exception_handler(EmailInvalidoError)
    async def email_invalido_handler(request: Request, exc: EmailInvalidoError):
        return _json_error(
            HTTPStatus.BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
            str(exc),
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError):
        return _json_error(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            ErrorCode.VALIDATION_ERROR,
            "Erro de validação",
            details=exc.errors(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)

        if exc.status_code == HTTPStatus.UNAUTHORIZED:
            code = ErrorCode.UNAUTHORIZED
        elif exc.status_code == HTTPStatus.FORBIDDEN:
            code = ErrorCode.FORBIDDEN
        elif exc.status_code == HTTPStatus.NOT_FOUND:
            code = ErrorCode.NOT_FOUND
        else:
            code = ErrorCode.VALIDATION_ERROR

        return _json_error(HTTPStatus(exc.status_code), code, str(exc.detail))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        return _json_error(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            ErrorCode.VALIDATION_ERROR,
            "Erro interno",
        )
