from decimal import Decimal

import pytest

from trading_system.integrations.kis import HttpResponse, KisApiClient


def test_kis_api_client_preflight_symbol_fetches_token_and_quote() -> None:
    client = KisApiClient.from_env(
        secret_provider=_StubSecretProvider(),
        transport=_StubTransport(),
    )

    quote = client.preflight_symbol("005930")

    assert quote.symbol == "005930"
    assert quote.price == Decimal("70300")
    assert quote.volume == Decimal("123456")


def test_kis_api_client_requires_access_token_in_response() -> None:
    client = KisApiClient.from_env(
        secret_provider=_StubSecretProvider(),
        transport=_MissingTokenTransport(),
    )

    with pytest.raises(RuntimeError, match="access_token"):
        client.preflight_symbol("005930")


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
        return HttpResponse(
            status_code=200,
            body={"output": {"stck_prpr": "70300", "acml_vol": "123456"}},
        )


class _MissingTokenTransport:
    def request(self, method: str, url: str, *, headers: dict[str, str], body=None) -> HttpResponse:
        del method, url, headers, body
        return HttpResponse(status_code=200, body={})
