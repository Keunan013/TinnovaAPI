from __future__ import annotations

import pytest

from http import HTTPStatus
from typing import Any
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.error_handler import register_error_handlers
from app.core.enums.error_code import ErrorCode
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


def _extract_payload(resp: JSONResponse) -> dict[str, Any]:
    import json
    return json.loads(resp.body.decode("utf-8"))


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)
    return app


@pytest.mark.anyio
async def test_placa_duplicada_handler(app: FastAPI):
    handler = app.exception_handlers[PlacaDuplicadaError]
    resp = await handler(None, PlacaDuplicadaError())
    payload = _extract_payload(resp)
    assert resp.status_code == HTTPStatus.CONFLICT.value
    assert payload["error"]["code"] == ErrorCode.PLACA_DUPLICADA.value
    assert payload["error"]["message"] == "Placa já cadastrada"
    assert "details" not in payload["error"] or payload["error"]["details"] is None


@pytest.mark.anyio
async def test_veiculo_not_found_handler(app: FastAPI):
    handler = app.exception_handlers[VeiculoNaoEncontradoError]
    resp = await handler(None, VeiculoNaoEncontradoError())
    payload = _extract_payload(resp)
    assert resp.status_code == HTTPStatus.NOT_FOUND.value
    assert payload["error"]["code"] == ErrorCode.NOT_FOUND.value
    assert payload["error"]["message"] == "Veículo não encontrado"


@pytest.mark.anyio
async def test_invalid_update_handler(app: FastAPI):
    handler = app.exception_handlers[InvalidUpdateError]
    exc = InvalidUpdateError("campo inválido")
    resp = await handler(None, exc)
    payload = _extract_payload(resp)
    assert resp.status_code == HTTPStatus.BAD_REQUEST.value
    assert payload["error"]["code"] == ErrorCode.INVALID_UPDATE.value
    assert payload["error"]["message"] == "campo inválido"


@pytest.mark.anyio
async def test_fx_unavailable_handler(app: FastAPI):
    handler = app.exception_handlers[FxRateUnavailableError]
    resp = await handler(None, FxRateUnavailableError("x"))
    payload = _extract_payload(resp)
    assert resp.status_code == HTTPStatus.SERVICE_UNAVAILABLE.value
    assert payload["error"]["code"] == ErrorCode.FX_UNAVAILABLE.value
    assert payload["error"]["message"] == "Não foi possível obter cotação USD-BRL"


@pytest.mark.anyio
async def test_email_duplicado_handler(app: FastAPI):
    handler = app.exception_handlers[EmailDuplicadoError]
    resp = await handler(None, EmailDuplicadoError())
    payload = _extract_payload(resp)
    assert resp.status_code == HTTPStatus.CONFLICT.value
    assert payload["error"]["code"] == ErrorCode.VALIDATION_ERROR.value
    assert payload["error"]["message"] == "Email já cadastrado"


@pytest.mark.anyio
async def test_user_not_found_handler(app: FastAPI):
    handler = app.exception_handlers[UserNaoEncontradoError]
    resp = await handler(None, UserNaoEncontradoError())
    payload = _extract_payload(resp)
    assert resp.status_code == HTTPStatus.NOT_FOUND.value
    assert payload["error"]["code"] == ErrorCode.NOT_FOUND.value
    assert payload["error"]["message"] == "Usuário não encontrado"


@pytest.mark.anyio
async def test_credenciais_invalidas_handler(app: FastAPI):
    handler = app.exception_handlers[CredenciaisInvalidasError]
    resp = await handler(None, CredenciaisInvalidasError())
    payload = _extract_payload(resp)
    assert resp.status_code == HTTPStatus.UNAUTHORIZED.value
    assert payload["error"]["code"] == ErrorCode.UNAUTHORIZED.value
    assert payload["error"]["message"] == "Credenciais inválidas"


@pytest.mark.anyio
async def test_senha_invalida_handler(app: FastAPI):
    handler = app.exception_handlers[SenhaInvalidaError]
    resp = await handler(None, SenhaInvalidaError("senha fraca"))
    payload = _extract_payload(resp)
    assert resp.status_code == HTTPStatus.BAD_REQUEST.value
    assert payload["error"]["code"] == ErrorCode.VALIDATION_ERROR.value
    assert payload["error"]["message"] == "senha fraca"


@pytest.mark.anyio
async def test_email_invalido_handler(app: FastAPI):
    handler = app.exception_handlers[EmailInvalidoError]
    resp = await handler(None, EmailInvalidoError("email inválido"))
    payload = _extract_payload(resp)
    assert resp.status_code == HTTPStatus.BAD_REQUEST.value
    assert payload["error"]["code"] == ErrorCode.VALIDATION_ERROR.value
    assert payload["error"]["message"] == "email inválido"


@pytest.mark.anyio
async def test_request_validation_handler(app: FastAPI):
    handler = app.exception_handlers[RequestValidationError]

    class _Model(BaseModel):
        x: int

    try:
        _Model(x="abc")
    except ValidationError as ve:
        exc = RequestValidationError(ve.errors())

    resp = await handler(None, exc)

    payload = _extract_payload(resp)
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY.value
    assert payload["error"]["code"] == ErrorCode.VALIDATION_ERROR.value
    assert payload["error"]["message"] == "Erro de validação"
    assert isinstance(payload["error"]["details"], list)
    assert payload["error"]["details"], "Esperava detalhes de validação"


@pytest.mark.anyio
async def test_http_exception_handler_keeps_standard_payload(app: FastAPI):
    handler = app.exception_handlers[StarletteHTTPException]

    detail = {"error": {"code": "X", "message": "Y"}}
    exc = StarletteHTTPException(status_code=HTTPStatus.FORBIDDEN.value, detail=detail)

    resp = await handler(None, exc)

    payload = _extract_payload(resp)
    assert resp.status_code == HTTPStatus.FORBIDDEN.value
    assert payload == detail


@pytest.mark.anyio
@pytest.mark.parametrize(
    "status_code, expected_error_code",
    [
        (HTTPStatus.UNAUTHORIZED.value, ErrorCode.UNAUTHORIZED.value),
        (HTTPStatus.FORBIDDEN.value, ErrorCode.FORBIDDEN.value),
        (HTTPStatus.NOT_FOUND.value, ErrorCode.NOT_FOUND.value),
        (HTTPStatus.BAD_REQUEST.value, ErrorCode.VALIDATION_ERROR.value),
    ],
)
async def test_http_exception_handler_maps_status_to_error_code(
    app: FastAPI, status_code: int, expected_error_code: str
):
    handler = app.exception_handlers[StarletteHTTPException]
    exc = StarletteHTTPException(status_code=status_code, detail="boom")

    resp = await handler(None, exc)

    payload = _extract_payload(resp)
    assert resp.status_code == status_code
    assert payload["error"]["code"] == expected_error_code
    assert payload["error"]["message"] == "boom"


@pytest.mark.anyio
async def test_unhandled_exception_handler_returns_500(app: FastAPI):
    handler = app.exception_handlers[Exception]

    resp = await handler(None, RuntimeError("x"))

    payload = _extract_payload(resp)
    assert resp.status_code == HTTPStatus.INTERNAL_SERVER_ERROR.value
    assert payload["error"]["code"] == ErrorCode.VALIDATION_ERROR.value
    assert payload["error"]["message"] == "Erro interno"
