from __future__ import annotations

from fastapi import HTTPException
from typing import Any, Dict, Optional

from app.core.enums.error_code import ErrorCode
from app.schemas.error import ErrorResponse, ErrorInfo


def api_error_payload(code: ErrorCode, message: str, details: Optional[Any] = None) -> Dict[str, Any]:
    payload = ErrorResponse(error=ErrorInfo(code=code, message=message, details=details))
    return payload.model_dump(exclude_none=True)


def raise_api_error(status_code: int, code: ErrorCode, message: str, details: Optional[Any] = None) -> None:
    raise HTTPException(status_code=status_code, detail=api_error_payload(code, message, details))
