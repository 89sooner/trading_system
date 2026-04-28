from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

import pytest

from trading_system.core.types import MarketBar
from trading_system.execution.kis_adapter import KisBrokerAdapter
from trading_system.execution.orders import OrderRequest, OrderSide
from trading_system.integrations.kis import (
    KST,
    HttpResponse,
    KisApiClient,
    KisQuote,
    KisResponseError,
    _validate_quote,
    is_krx_market_open,
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


def test_kis_api_client_reuses_access_token_for_repeated_calls() -> None:
    transport = _CountingTokenTransport()
    client = KisApiClient.from_env(
        secret_provider=_StubSecretProvider(),
        transport=transport,
    )

    client.preflight_symbol("005930")
    client.preflight_symbol("005930")

    assert transport.token_requests == 1
    assert transport.price_requests == 2


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
    assert fill.broker_order_id == "12345"


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


def test_kis_quote_validation_rejects_zero_price() -> None:
    quote = KisQuote(
        symbol="005930",
        price=Decimal("0"),
        volume=Decimal("1000"),
        as_of=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )

    with pytest.raises(KisResponseError, match="invalid price"):
        _validate_quote(quote)


def test_kis_quote_validation_rejects_negative_volume() -> None:
    quote = KisQuote(
        symbol="005930",
        price=Decimal("70300"),
        volume=Decimal("-1"),
        as_of=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )

    with pytest.raises(KisResponseError, match="invalid volume"):
        _validate_quote(quote)


def test_kis_quote_validation_passes_valid_quote() -> None:
    quote = KisQuote(
        symbol="005930",
        price=Decimal("70300"),
        volume=Decimal("0"),
        as_of=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )

    result = _validate_quote(quote)

    assert result.symbol == "005930"
    assert result.price == Decimal("70300")
    assert result.volume == Decimal("0")


def test_kis_order_result_includes_receipt_metadata() -> None:
    client = KisApiClient.from_env(
        secret_provider=_StubSecretProvider(),
        transport=_OrderSuccessTransport(),
    )

    result = client.submit_order(
        OrderRequest(symbol="005930", side=OrderSide.BUY, quantity=Decimal("1"))
    )

    assert result.result_code == "0"
    assert result.message != ""


def test_kis_api_client_inquire_balance_returns_structured_data() -> None:
    client = KisApiClient.from_env(
        secret_provider=_StubSecretProvider(),
        transport=_BalanceTransport(),
    )

    balance = client.inquire_balance(access_token="kis-access-token")

    assert "cash" in balance
    assert "positions" in balance
    assert "average_costs" in balance
    assert "pending_symbols" in balance
    assert balance["cash"] == Decimal("5000000")
    assert balance["positions"]["005930"] == Decimal("10")
    assert balance["average_costs"]["005930"] == Decimal("70000")


def test_kis_api_client_inquire_balance_marks_pending_symbols_from_available_quantity() -> None:
    client = KisApiClient.from_env(
        secret_provider=_StubSecretProvider(),
        transport=_PendingBalanceTransport(),
    )

    balance = client.inquire_balance(access_token="kis-access-token")

    assert balance["pending_symbols"] == ("005930",)


def test_kis_api_client_inquire_balance_requires_pending_signal_for_held_symbol() -> None:
    client = KisApiClient.from_env(
        secret_provider=_StubSecretProvider(),
        transport=_MissingPendingSignalBalanceTransport(),
    )

    with pytest.raises(KisResponseError, match="missing ord_psbl_qty"):
        client.inquire_balance(access_token="kis-access-token")


def test_kis_broker_adapter_returns_none_when_pending_signal_is_unavailable() -> None:
    client = KisApiClient.from_env(
        secret_provider=_StubSecretProvider(),
        transport=_MissingPendingSignalBalanceTransport(),
    )
    adapter = KisBrokerAdapter(client=client)

    assert adapter.get_account_balance() is None


def test_kis_api_client_inquire_open_orders_returns_snapshot() -> None:
    client = KisApiClient.from_env(
        secret_provider=_StubSecretProvider(),
        transport=_OpenOrdersTransport(),
    )

    snapshot = client.inquire_open_orders(access_token="kis-access-token")

    assert snapshot.pending_symbols == ("005930",)
    assert snapshot.orders[0].broker_order_id == "90001"
    assert snapshot.orders[0].side == OrderSide.BUY
    assert snapshot.orders[0].remaining_quantity == Decimal("2")


def test_kis_api_client_inquire_open_orders_ignores_fully_filled_orders() -> None:
    client = KisApiClient.from_env(
        secret_provider=_StubSecretProvider(),
        transport=_NoOpenOrdersTransport(),
    )

    snapshot = client.inquire_open_orders(access_token="kis-access-token")

    assert snapshot.orders == ()
    assert snapshot.pending_symbols == ()


def test_kis_api_client_inquire_open_orders_requires_order_id() -> None:
    client = KisApiClient.from_env(
        secret_provider=_StubSecretProvider(),
        transport=_MalformedOpenOrdersTransport(),
    )

    with pytest.raises(KisResponseError, match="order id"):
        client.inquire_open_orders(access_token="kis-access-token")


def test_is_krx_market_open_during_trading_hours() -> None:
    # Monday at 10:00 KST
    now = datetime(2024, 1, 8, 10, 0, 0, tzinfo=KST)

    assert is_krx_market_open(now=now) is True


def test_is_krx_market_open_outside_trading_hours() -> None:
    # Monday at 16:00 KST
    now = datetime(2024, 1, 8, 16, 0, 0, tzinfo=KST)

    assert is_krx_market_open(now=now) is False


def test_is_krx_market_open_on_weekend() -> None:
    # Saturday at 10:00 KST
    now = datetime(2024, 1, 6, 10, 0, 0, tzinfo=KST)

    assert is_krx_market_open(now=now) is False


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


class _CountingTokenTransport:
    def __init__(self) -> None:
        self.token_requests = 0
        self.price_requests = 0

    def request(self, method: str, url: str, *, headers: dict[str, str], body=None) -> HttpResponse:
        if method == "POST" and url.endswith("/oauth2/tokenP"):
            self.token_requests += 1
            return HttpResponse(
                status_code=200,
                body={"access_token": "kis-access-token", "expires_in": "86400"},
            )

        self.price_requests += 1
        assert headers["authorization"] == "Bearer kis-access-token"
        return HttpResponse(
            status_code=200,
            body={"output": {"stck_prpr": "70300", "acml_vol": "123456"}},
        )


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


class _BalanceTransport:
    def request(self, method: str, url: str, *, headers: dict[str, str], body=None) -> HttpResponse:
        del method, url, headers, body
        return HttpResponse(
            status_code=200,
            body={
                "output1": [
                    {
                        "pdno": "005930",
                        "hldg_qty": "10",
                        "pchs_avg_pric": "70000",
                        "ord_psbl_qty": "10",
                    },
                ],
                "output2": [{"dnca_tot_amt": "5000000"}],
            },
        )


class _PendingBalanceTransport:
    def request(self, method: str, url: str, *, headers: dict[str, str], body=None) -> HttpResponse:
        del method, url, headers, body
        return HttpResponse(
            status_code=200,
            body={
                "output1": [
                    {
                        "pdno": "005930",
                        "hldg_qty": "10",
                        "pchs_avg_pric": "70000",
                        "ord_psbl_qty": "7",
                    },
                ],
                "output2": [{"dnca_tot_amt": "5000000"}],
            },
        )


class _MissingPendingSignalBalanceTransport:
    def request(self, method: str, url: str, *, headers: dict[str, str], body=None) -> HttpResponse:
        del method, url, headers, body
        return HttpResponse(
            status_code=200,
            body={
                "output1": [
                    {
                        "pdno": "005930",
                        "hldg_qty": "10",
                        "pchs_avg_pric": "70000",
                    },
                ],
                "output2": [{"dnca_tot_amt": "5000000"}],
            },
        )


class _OpenOrdersTransport:
    def request(self, method: str, url: str, *, headers: dict[str, str], body=None) -> HttpResponse:
        del headers, body
        assert method == "GET"
        assert "/inquire-psbl-rvsecncl" in url
        return HttpResponse(
            status_code=200,
            body={
                "rt_cd": "0",
                "output": [
                    {
                        "odno": "90001",
                        "pdno": "005930",
                        "sll_buy_dvsn_cd": "02",
                        "ord_qty": "5",
                        "tot_ccld_qty": "3",
                        "ord_stat_name": "open",
                        "ord_tmd": "093000",
                    }
                ],
            },
        )


class _NoOpenOrdersTransport:
    def request(self, method: str, url: str, *, headers: dict[str, str], body=None) -> HttpResponse:
        del method, url, headers, body
        return HttpResponse(
            status_code=200,
            body={
                "rt_cd": "0",
                "output": [
                    {
                        "odno": "90002",
                        "pdno": "005930",
                        "sll_buy_dvsn_cd": "02",
                        "ord_qty": "5",
                        "tot_ccld_qty": "5",
                    }
                ],
            },
        )


class _MalformedOpenOrdersTransport:
    def request(self, method: str, url: str, *, headers: dict[str, str], body=None) -> HttpResponse:
        del method, url, headers, body
        return HttpResponse(
            status_code=200,
            body={
                "rt_cd": "0",
                "output": [
                    {
                        "pdno": "005930",
                        "sll_buy_dvsn_cd": "02",
                        "ord_qty": "5",
                    }
                ],
            },
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
