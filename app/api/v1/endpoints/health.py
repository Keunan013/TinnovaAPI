from __future__ import annotations

from http import HTTPStatus
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.infra import get_redis
from app.core.schemas.health_checks import HealthChecks, HealthStatus
from app.schemas.health_response import HealthResponse
from app.api.api_key import require_api_key
from app.services.fx.fx_provider import FxProvider
from app.services.fx.deps import get_fx_provider

router = APIRouter(tags=["health"])


@router.get("/health/ready",
            status_code=HTTPStatus.OK,
            response_model=HealthResponse,
            response_model_exclude_none=True,
            dependencies=[Depends(require_api_key)]
            )
async def health_ready(
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    fx: FxProvider = Depends(get_fx_provider),
) -> HealthResponse:
    db_status: HealthStatus = HealthStatus.OK
    redis_status: HealthStatus = HealthStatus.OK

    # DB
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = HealthStatus.ERROR

    # Redis
    try:
        await redis.ping()
    except Exception:
        redis_status = HealthStatus.ERROR

    # FX
    try:
        rate = await fx.usd_brl_rate()
        fx_status = HealthStatus.OK if rate.usd_brl > 0 else HealthStatus.ERROR
    except Exception:
        fx_status = HealthStatus.ERROR

    checks = HealthChecks(
        database=db_status,
        redis=redis_status,
        fx_provider=fx_status,
    )

    overall: HealthStatus = HealthStatus.OK if all(v == HealthStatus.OK for v in checks.__dict__.values()) else HealthStatus.DEGRADED

    response = HealthResponse(
        status=overall,
        checks=checks,
    )
    return response
