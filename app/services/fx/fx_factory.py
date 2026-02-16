import httpx
import redis.asyncio as redis

from app.core.config import settings
from app.services.fx.fx_provider import RedisCachedFxProvider


def build_fx_provider() -> RedisCachedFxProvider:
    redis_client = redis.from_url(settings.redis_url, decode_responses=False)
    http_client = httpx.AsyncClient()
    return RedisCachedFxProvider(redis_client=redis_client, http_client=http_client)
