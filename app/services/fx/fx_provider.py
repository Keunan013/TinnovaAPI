from __future__ import annotations

import httpx
import redis.asyncio as redis

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from app.core.config import settings
from app.domain.fx_rate import FxRate
from app.exceptions.fx_rate_exceptions import FxRateUnavailableError


def _q2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class FxProvider:
    async def usd_brl_rate(self) -> FxRate:
        raise NotImplementedError

    async def brl_to_usd(self, valor_brl: Decimal) -> Decimal:
        rate = await self.usd_brl_rate()
        if rate.usd_brl <= 0:
            raise FxRateUnavailableError("Cotação inválida (<= 0)")
        # BRL -> USD = BRL / (BRL por USD)
        return _q2(valor_brl / rate.usd_brl)


class RedisCachedFxProvider(FxProvider):
    def __init__(
        self,
        redis_client: redis.Redis,
        http_client: httpx.AsyncClient,
        cache_key: str = "fx:usd_brl",
        ttl_seconds: int = 300,  # 5 min
    ):
        self.redis = redis_client
        self.http = http_client
        self.cache_key = cache_key
        self.ttl_seconds = ttl_seconds

    async def usd_brl_rate(self) -> FxRate:
        cached = await self.redis.get(self.cache_key)
        if cached:
            return FxRate(usd_brl=Decimal(cached.decode("utf-8")))

        rate = await self._fetch_awesome()
        if rate is None:
            rate = await self._fetch_frankfurter()

        if rate is None:
            raise FxRateUnavailableError("Falha ao obter cotação USD->BRL")

        await self.redis.set(self.cache_key, str(rate.usd_brl), ex=self.ttl_seconds)
        return rate

    async def _fetch_awesome(self) -> Optional[FxRate]:
        try:
            resp = await self.http.get(settings.awesome_api_url, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            usdbrl = data.get("USDBRL") or {}
            bid = usdbrl.get("bid")
            if not bid:
                return None
            return FxRate(usd_brl=Decimal(str(bid)))
        except Exception:
            return None

    async def _fetch_frankfurter(self) -> Optional[FxRate]:
        try:
            resp = await self.http.get(settings.frankfurter_api_url, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            rates = data.get("rates") or {}
            brl = rates.get("BRL")
            if brl is None:
                return None
            return FxRate(usd_brl=Decimal(str(brl)))
        except Exception:
            return None
