from fastapi import Request

from app.services.fx.fx_provider import FxProvider, RedisCachedFxProvider


def get_fx_provider(request: Request) -> FxProvider:
    redis_client = request.app.state.redis
    http_client = request.app.state.http
    return RedisCachedFxProvider(redis_client=redis_client, http_client=http_client)
