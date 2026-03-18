from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from trading_system.core.compat import UTC
from trading_system.core.ops import EnvSecretProvider, SecretProvider


@dataclass(slots=True)
class KisCredentials:
    app_key: str
    app_secret: str
    account_number: str
    product_code: str


@dataclass(slots=True)
class KisQuote:
    symbol: str
    price: Decimal
    volume: Decimal
    as_of: datetime


@dataclass(slots=True)
class HttpResponse:
    status_code: int
    body: dict[str, Any]


class HttpTransport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
    ) -> HttpResponse:
        """Execute one HTTP request."""


class UrllibHttpTransport:
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
    ) -> HttpResponse:
        encoded_body = None
        request_headers = dict(headers)
        if body is not None:
            encoded_body = json.dumps(body).encode("utf-8")
            request_headers.setdefault("content-type", "application/json")

        request = Request(
            url=url,
            data=encoded_body,
            headers=request_headers,
            method=method.upper(),
        )
        try:
            with urlopen(request, timeout=5) as response:
                payload = response.read().decode("utf-8")
                parsed = json.loads(payload) if payload else {}
                return HttpResponse(status_code=response.status, body=parsed)
        except HTTPError as exc:
            payload = exc.read().decode("utf-8")
            parsed = json.loads(payload) if payload else {}
            raise RuntimeError(
                f"KIS HTTP error {exc.code}: {parsed.get('msg1', exc.reason)}"
            ) from exc
        except URLError as exc:
            raise OSError(f"KIS transport unavailable: {exc.reason}") from exc


class KisApiClient:
    _PROD_BASE_URL = "https://openapi.koreainvestment.com:9443"
    _MOCK_BASE_URL = "https://openapivts.koreainvestment.com:29443"

    def __init__(
        self,
        credentials: KisCredentials,
        *,
        transport: HttpTransport | None = None,
        base_url: str | None = None,
    ) -> None:
        self._credentials = credentials
        self._transport = transport or UrllibHttpTransport()
        self._base_url = (base_url or os.getenv("TRADING_SYSTEM_KIS_BASE_URL") or "").rstrip("/")
        if not self._base_url:
            self._base_url = self._PROD_BASE_URL

    @classmethod
    def from_env(
        cls,
        *,
        secret_provider: SecretProvider | None = None,
        transport: HttpTransport | None = None,
    ) -> "KisApiClient":
        provider = secret_provider or EnvSecretProvider()
        credentials = KisCredentials(
            app_key=provider.get_secret("TRADING_SYSTEM_KIS_APP_KEY"),
            app_secret=provider.get_secret("TRADING_SYSTEM_KIS_APP_SECRET"),
            account_number=provider.get_secret("TRADING_SYSTEM_KIS_CANO"),
            product_code=provider.get_secret("TRADING_SYSTEM_KIS_ACNT_PRDT_CD"),
        )
        environment = os.getenv("TRADING_SYSTEM_KIS_ENV", "prod").strip().lower()
        default_base_url = (
            cls._MOCK_BASE_URL
            if environment in {"mock", "paper", "sandbox"}
            else cls._PROD_BASE_URL
        )
        return cls(credentials=credentials, transport=transport, base_url=default_base_url)

    def preflight_symbol(self, symbol: str) -> KisQuote:
        access_token = self._issue_access_token()
        return self.inquire_price(symbol=symbol, access_token=access_token)

    def inquire_price(self, symbol: str, *, access_token: str) -> KisQuote:
        params = urlencode(
            {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": symbol,
            }
        )
        response = self._transport.request(
            "GET",
            f"{self._base_url}/uapi/domestic-stock/v1/quotations/inquire-price?{params}",
            headers={
                "authorization": f"Bearer {access_token}",
                "appkey": self._credentials.app_key,
                "appsecret": self._credentials.app_secret,
                "tr_id": os.getenv("TRADING_SYSTEM_KIS_PRICE_TR_ID", "FHKST01010100"),
            },
        )
        output = _as_dict(response.body.get("output"), "output")
        current_price = _as_decimal(output.get("stck_prpr"), "stck_prpr")
        volume = _as_decimal(output.get("acml_vol"), "acml_vol", default=Decimal("0"))
        return KisQuote(
            symbol=symbol,
            price=current_price,
            volume=volume,
            as_of=datetime.now(tz=UTC),
        )

    def _issue_access_token(self) -> str:
        response = self._transport.request(
            "POST",
            f"{self._base_url}/oauth2/tokenP",
            headers={"content-type": "application/json"},
            body={
                "grant_type": "client_credentials",
                "appkey": self._credentials.app_key,
                "appsecret": self._credentials.app_secret,
            },
        )
        access_token = response.body.get("access_token")
        if not isinstance(access_token, str) or not access_token.strip():
            raise RuntimeError("KIS token response did not include a usable access_token.")
        return access_token


def _as_dict(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError(f"KIS response field '{field_name}' was missing or invalid.")
    return value


def _as_decimal(value: Any, field_name: str, *, default: Decimal | None = None) -> Decimal:
    if value in (None, ""):
        if default is not None:
            return default
        raise RuntimeError(f"KIS response field '{field_name}' was missing.")
    try:
        return Decimal(str(value))
    except Exception as exc:  # pragma: no cover - defensive parser path
        raise RuntimeError(f"KIS response field '{field_name}' was not numeric.") from exc
