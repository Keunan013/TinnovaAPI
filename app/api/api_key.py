from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader
from http import HTTPStatus

from app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)


def require_api_key(api_key: str | None = Security(api_key_header)) -> None:
    if not api_key or api_key != settings.api_key:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="Invalid API key")
