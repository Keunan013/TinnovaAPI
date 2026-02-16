# tests/unit/services/fx/test_fx_provider.py
from __future__ import annotations

import pytest

from decimal import Decimal
from unittest.mock import AsyncMock

import app.services.fx.fx_provider as fx_module


class _FakeResp:
    def __init__(self, *, payload: dict, raise_for_status_exc: Exception | None = None):
        self._payload = payload
        self._raise_for_status_exc = raise_for_status_exc

    def raise_for_status(self) -> None:
        if self._raise_for_status_exc:
            raise self._raise_for_status_exc

    def json(self) -> dict:
        return self._payload


@pytest.mark.anyio
async def test_q2_quantiza_2_casas():
    assert fx_module._q2(Decimal("1")) == Decimal("1.00")
    assert fx_module._q2(Decimal("1.234")) == Decimal("1.23")
    assert fx_module._q2(Decimal("1.235")) == Decimal("1.24")


@pytest.mark.anyio
async def test_brl_to_usd_quando_rate_invalido_deve_levantar_fx_unavailable():
    class _P(fx_module.FxProvider):
        async def usd_brl_rate(self) -> fx_module.FxRate:
            return fx_module.FxRate(usd_brl=Decimal("0"))

    p = _P()

    with pytest.raises(fx_module.FxRateUnavailableError):
        await p.brl_to_usd(Decimal("10.00"))


@pytest.mark.anyio
async def test_brl_to_usd_converte_dividindo_pelo_rate_e_quantiza():
    class _P(fx_module.FxProvider):
        async def usd_brl_rate(self) -> fx_module.FxRate:
            return fx_module.FxRate(usd_brl=Decimal("5.00"))

    p = _P()

    assert await p.brl_to_usd(Decimal("10")) == Decimal("2.00")


@pytest.mark.anyio
async def test_usd_brl_rate_retorna_cache_quando_existir():
    redis_client = AsyncMock()
    http_client = AsyncMock()

    redis_client.get.return_value = b"5.12"

    provider = fx_module.RedisCachedFxProvider(redis_client=redis_client, http_client=http_client)

    rate = await provider.usd_brl_rate()

    assert rate.usd_brl == Decimal("5.12")
    redis_client.get.assert_awaited_once_with(provider.cache_key)
    http_client.get.assert_not_awaited()
    redis_client.set.assert_not_awaited()


@pytest.mark.anyio
async def test_usd_brl_rate_busca_awesome_e_salva_cache():
    redis_client = AsyncMock()
    http_client = AsyncMock()

    redis_client.get.return_value = None

    fx_module.settings.awesome_api_url = "https://awesome.test"
    fx_module.settings.frankfurter_api_url = "https://frank.test"

    http_client.get.return_value = _FakeResp(payload={"USDBRL": {"bid": "5.55"}})

    provider = fx_module.RedisCachedFxProvider(
        redis_client=redis_client,
        http_client=http_client,
        cache_key="fx:usd_brl",
        ttl_seconds=300,
    )

    rate = await provider.usd_brl_rate()

    assert rate.usd_brl == Decimal("5.55")
    http_client.get.assert_awaited_once()  # awesome chamado
    redis_client.set.assert_awaited_once_with("fx:usd_brl", "5.55", ex=300)


@pytest.mark.anyio
async def test_usd_brl_rate_fallback_para_frankfurter_quando_awesome_nao_tem_bid():
    redis_client = AsyncMock()
    http_client = AsyncMock()

    redis_client.get.return_value = None

    fx_module.settings.awesome_api_url = "https://awesome.test"
    fx_module.settings.frankfurter_api_url = "https://frank.test"

    http_client.get.side_effect = [
        _FakeResp(payload={"USDBRL": {}}),
        _FakeResp(payload={"rates": {"BRL": "5.99"}}),
    ]

    provider = fx_module.RedisCachedFxProvider(redis_client=redis_client, http_client=http_client)

    rate = await provider.usd_brl_rate()

    assert rate.usd_brl == Decimal("5.99")
    assert http_client.get.await_count == 2
    redis_client.set.assert_awaited_once()
    args, kwargs = redis_client.set.await_args
    assert args[0] == provider.cache_key
    assert args[1] == "5.99"
    assert kwargs["ex"] == provider.ttl_seconds


@pytest.mark.anyio
async def test_usd_brl_rate_fallback_para_frankfurter_quando_awesome_da_erro():
    redis_client = AsyncMock()
    http_client = AsyncMock()

    redis_client.get.return_value = None

    fx_module.settings.awesome_api_url = "https://awesome.test"
    fx_module.settings.frankfurter_api_url = "https://frank.test"

    http_client.get.side_effect = [
        _FakeResp(payload={}, raise_for_status_exc=RuntimeError("boom")),
        _FakeResp(payload={"rates": {"BRL": 5.01}}),
    ]

    provider = fx_module.RedisCachedFxProvider(redis_client=redis_client, http_client=http_client)

    rate = await provider.usd_brl_rate()

    assert rate.usd_brl == Decimal("5.01")
    assert http_client.get.await_count == 2
    redis_client.set.assert_awaited_once()


@pytest.mark.anyio
async def test_usd_brl_rate_quando_awesome_e_frankfurter_falham_deve_levantar():
    redis_client = AsyncMock()
    http_client = AsyncMock()

    redis_client.get.return_value = None

    fx_module.settings.awesome_api_url = "https://awesome.test"
    fx_module.settings.frankfurter_api_url = "https://frank.test"

    http_client.get.side_effect = [
        _FakeResp(payload={"USDBRL": {}}),
        _FakeResp(payload={"rates": {}}),
    ]

    provider = fx_module.RedisCachedFxProvider(redis_client=redis_client, http_client=http_client)

    with pytest.raises(fx_module.FxRateUnavailableError):
        await provider.usd_brl_rate()

    assert http_client.get.await_count == 2
    redis_client.set.assert_not_awaited()


@pytest.mark.anyio
async def test_fetch_awesome_retorna_none_quando_nao_tem_USDBRL():
    redis_client = AsyncMock()
    http_client = AsyncMock()
    fx_module.settings.awesome_api_url = "https://awesome.test"

    http_client.get.return_value = _FakeResp(payload={"X": 1})

    provider = fx_module.RedisCachedFxProvider(redis_client=redis_client, http_client=http_client)
    rate = await provider._fetch_awesome()

    assert rate is None


@pytest.mark.anyio
async def test_fetch_frankfurter_retorna_none_quando_nao_tem_BRL():
    redis_client = AsyncMock()
    http_client = AsyncMock()
    fx_module.settings.frankfurter_api_url = "https://frank.test"

    http_client.get.return_value = _FakeResp(payload={"rates": {"EUR": "1.0"}})

    provider = fx_module.RedisCachedFxProvider(redis_client=redis_client, http_client=http_client)
    rate = await provider._fetch_frankfurter()

    assert rate is None


@pytest.mark.anyio
async def test_fetch_frankfurter_retorna_none_quando_request_quebra():
    redis_client = AsyncMock()
    http_client = AsyncMock()
    fx_module.settings.frankfurter_api_url = "https://frank.test"

    http_client.get.side_effect = RuntimeError("network down")

    provider = fx_module.RedisCachedFxProvider(redis_client=redis_client, http_client=http_client)
    rate = await provider._fetch_frankfurter()

    assert rate is None
