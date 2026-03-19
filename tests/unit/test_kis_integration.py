from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

import pytest

from trading_system.core.types import MarketBar
from trading_system.execution.kis_adapter import KisBrokerAdapter
from trading_system.execution.orders import OrderRequest, OrderSide
from trading_system.integrations.kis import (
    HttpResponse,
    KisApiClient,
    KisResponseError,
)


def test_kis_api_client_preflight_symbol_fetches_token_and_quote() -> None:
    client = KisApiClient.from_env(
        secret_provider=_StubSecretProvider(),
        transport=_StubTransport(),
    )

    quote = client.preflight_symbol("005930")

    assert quote.symbol == "005930"
    assert quote.price == Decimal("70300")
    assert quote.volume == Decimal("123456")


def test_kis_api_client_inquire_price_uses_default_market_div_code() -> None:
    client = KisApiClient.from_env(
        secret_provider=_StubSecretProvider(),
        transport=_PriceTransport(expected_market_div="J"),
    )

    quote = client.preflight_symbol("005930")

    assert quote.symbol == "005930"


def test_kis_api_client_inquire_price_applies_custom_market_div_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRADING_SYSTEM_KIS_MARKET_DIV", "W")
    client = KisApiClient.from_env(
        secret_provider=_StubSecretProvider(),
        transport=_PriceTransport(expected_market_div="W"),
    )

    quote = client.preflight_symbol("005930")

    assert quote.symbol == "005930"


def test_kis_api_client_inquire_price_rejects_invalid_domestic_symbol() -> None:
    client = KisApiClient.from_env(
        secret_provider=_StubSecretProvider(),
        transport=_StubTransport(),
    )

    with pytest.raises(KisResponseError, match="input='5930'.*6-digit numeric code"):
        client.preflight_symbol("5930")


def test_kis_api_client_requires_access_token_in_response() -> None:
    client = KisApiClient.from_env(
        secret_provider=_StubSecretProvider(),
        transport=_MissingTokenTransport(),
    )

    with pytest.raises(KisResponseError, match="access_token"):
        client.preflight_symbol("005930")


def test_kis_broker_adapter_maps_successful_order_to_fill_event() -> None:
    client = KisApiClient.from_env(
        secret_provider=_StubSecretProvider(),
        transport=_OrderSuccessTransport(),
    )
    adapter = KisBrokerAdapter(client=client)

    fill = adapter.submit_order(
        OrderRequest(symbol="005930", side=OrderSide.BUY, quantity=Decimal("3")),
        _bar(),
    )

    assert fill.symbol == "005930"
    assert fill.requested_quantity == Decimal("3")
    assert fill.filled_quantity == Decimal("3")
    assert fill.fill_price == Decimal("70100")
    assert fill.status.value == "filled"


def test_kis_broker_adapter_maps_partial_fill_status() -> None:
    client = KisApiClient.from_env(
        secret_provider=_StubSecretProvider(),
        transport=_OrderPartialFillTransport(),
    )
    adapter = KisBrokerAdapter(client=client)

    fill = adapter.submit_order(
        OrderRequest(symbol="005930", side=OrderSide.SELL, quantity=Decimal("5")),
        _bar(),
    )

    assert fill.filled_quantity == Decimal("2")
    assert fill.status.value == "partially_filled"


def test_kis_api_client_submit_order_raises_response_error_on_rejection() -> None:
    client = KisApiClient.from_env(
        secret_provider=_StubSecretProvider(),
        transport=_OrderRejectedTransport(),
    )

    with pytest.raises(KisResponseError, match="order rejected"):
        client.submit_order(
            OrderRequest(symbol="005930", side=OrderSide.BUY, quantity=Decimal("1"))
        )


class _StubSecretProvider:
    def get_secret(self, name: str) -> str:
        values = {
            "TRADING_SYSTEM_KIS_APP_KEY": "app-key",
            "TRADING_SYSTEM_KIS_APP_SECRET": "app-secret",
            "TRADING_SYSTEM_KIS_CANO": "12345678",
            "TRADING_SYSTEM_KIS_ACNT_PRDT_CD": "01",
        }
        return values[name]


class _StubTransport:
    def request(self, method: str, url: str, *, headers: dict[str, str], body=None) -> HttpResponse:
        if method == "POST":
            assert url.endswith("/oauth2/tokenP")
            assert body == {
                "grant_type": "client_credentials",
                "appkey": "app-key",
                "appsecret": "app-secret",
            }
            return HttpResponse(status_code=200, body={"access_token": "kis-access-token"})

        assert headers["authorization"] == "Bearer kis-access-token"
        assert "FID_INPUT_ISCD=005930" in url
        assert "FID_COND_MRKT_DIV_CODE=J" in url
        return HttpResponse(
            status_code=200,
            body={"output": {"stck_prpr": "70300", "acml_vol": "123456"}},
        )


class _MissingTokenTransport:
    def request(self, method: str, url: str, *, headers: dict[str, str], body=None) -> HttpResponse:
        del method, url, headers, body
        return HttpResponse(status_code=200, body={})


class _OrderSuccessTransport:
    def request(self, method: str, url: str, *, headers: dict[str, str], body=None) -> HttpResponse:
        if method == "POST" and url.endswith("/oauth2/tokenP"):
            return HttpResponse(status_code=200, body={"access_token": "kis-access-token"})

        assert method == "POST"
        assert url.endswith("/uapi/domestic-stock/v1/trading/order-cash")
        assert headers["tr_id"] == "TTTC0802U"
        assert body["PDNO"] == "005930"
        return HttpResponse(
            status_code=200,
            body={
                "rt_cd": "0",
                "msg_cd": "APBK0013",
                "msg1": "정상처리",
                "output": {"ODNO": "12345", "ORD_QTY": "3", "ORD_UNPR": "70100"},
            },
        )


class _OrderPartialFillTransport:
    def request(self, method: str, url: str, *, headers: dict[str, str], body=None) -> HttpResponse:
        if method == "POST" and url.endswith("/oauth2/tokenP"):
            return HttpResponse(status_code=200, body={"access_token": "kis-access-token"})

        assert headers["tr_id"] == "TTTC0801U"
        return HttpResponse(
            status_code=200,
            body={
                "rt_cd": "0",
                "output": {"ODNO": "12346", "ORD_QTY": "2", "ORD_UNPR": "70000"},
            },
        )


class _OrderRejectedTransport:
    def request(self, method: str, url: str, *, headers: dict[str, str], body=None) -> HttpResponse:
        if method == "POST" and url.endswith("/oauth2/tokenP"):
            return HttpResponse(status_code=200, body={"access_token": "kis-access-token"})

        return HttpResponse(
            status_code=200,
            body={"rt_cd": "1", "msg_cd": "ERROR", "msg1": "주문 가능 수량 부족"},
        )


class _PriceTransport:
    def __init__(self, *, expected_market_div: str) -> None:
        self.expected_market_div = expected_market_div

    def request(self, method: str, url: str, *, headers: dict[str, str], body=None) -> HttpResponse:
        if method == "POST" and url.endswith("/oauth2/tokenP"):
            return HttpResponse(status_code=200, body={"access_token": "kis-access-token"})

        assert method == "GET"
        assert headers["authorization"] == "Bearer kis-access-token"
        query = parse_qs(urlparse(url).query)
        assert query["FID_COND_MRKT_DIV_CODE"] == [self.expected_market_div]
        assert query["FID_INPUT_ISCD"] == ["005930"]
        return HttpResponse(
            status_code=200,
            body={"output": {"stck_prpr": "70300", "acml_vol": "123456"}},
        )


def _bar() -> MarketBar:
    return MarketBar(
        symbol="005930",
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=Decimal("70000"),
        high=Decimal("70500"),
        low=Decimal("69900"),
        close=Decimal("70200"),
        volume=Decimal("1000"),
    )
