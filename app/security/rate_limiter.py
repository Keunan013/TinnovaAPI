from __future__ import annotations

import redis.asyncio as redis

from dataclasses import dataclass
from redis.exceptions import ConnectionError, TimeoutError

from app.core.config import settings
from app.exceptions.request_exceptions import TooManyRequestsError


@dataclass(frozen=True)
class RateLimitKey:
    ip: str
    username: str

    def as_redis_key(self) -> str:
        u = (self.username or "unknown").lower()
        return f"rl:login:{self.ip}:{u}"


class LoginRateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def hit(self, key: RateLimitKey) -> None:
        redis_key = key.as_redis_key()
        try:
            new_count = await self.redis.incr(redis_key)
            if new_count == 1:
                await self.redis.expire(redis_key, settings.login_rate_limit_window_seconds)
            if new_count > settings.login_rate_limit_max_attempts:
                await self.redis.expire(redis_key, settings.login_rate_limit_block_seconds)
                raise TooManyRequestsError(
                    retry_after_seconds=settings.login_rate_limit_block_seconds
                )
        except (ConnectionError, TimeoutError):
            return

    async def reset(self, key: RateLimitKey) -> None:
        try:
            await self.redis.delete(key.as_redis_key())
        except (ConnectionError, TimeoutError):
            return
