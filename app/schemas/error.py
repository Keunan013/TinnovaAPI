from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typing import Any, Optional

from app.core.enums.error_code import ErrorCode


class ErrorInfo(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    code: ErrorCode
    message: str
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    error: ErrorInfo
