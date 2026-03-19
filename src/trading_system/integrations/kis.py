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
from trading_system.execution.orders import OrderRequest, OrderSide


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
class KisOrderResult:
    order_id: str
    symbol: str
    side: OrderSide
    requested_quantity: Decimal
    filled_quantity: Decimal
    fill_price: Decimal
    fee: Decimal


@dataclass(slots=True)
class HttpResponse:
    status_code: int
    body: dict[str, Any]


class KisApiError(RuntimeError):
    """Base error for KIS API failures."""


class KisTransportError(KisApiError):
    """Raised when the transport layer cannot reach KIS."""


class KisHttpError(KisApiError):
    """Raised when KIS returns a non-success HTTP status."""


class KisResponseError(KisApiError):
    """Raised when KIS returns an invalid or failed payload."""


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
            raise KisHttpError(
                f"KIS HTTP error {exc.code}: {parsed.get('msg1', exc.reason)}"
            ) from exc
        except URLError as exc:
            raise KisTransportError(f"KIS transport unavailable: {exc.reason}") from exc


class KisApiClient:
    _PROD_BASE_URL = "https://openapi.koreainvestment.com:9443"
    _MOCK_BASE_URL = "https://openapivts.koreainvestment.com:29443"
    _PRICE_PATH = "/uapi/domestic-stock/v1/quotations/inquire-price"
    _ORDER_PATH = "/uapi/domestic-stock/v1/trading/order-cash"

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
        access_token = self.issue_access_token()
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
            f"{self._base_url}{self._PRICE_PATH}?{params}",
            headers={
                "authorization": f"Bearer {access_token}",
                "appkey": self._credentials.app_key,
                "appsecret": self._credentials.app_secret,
                "tr_id": self._price_tr_id(),
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

    def submit_order(self, order: OrderRequest) -> KisOrderResult:
        access_token = self.issue_access_token()
        response = self._transport.request(
            "POST",
            f"{self._base_url}{self._ORDER_PATH}",
            headers=self._order_headers(access_token=access_token, side=order.side),
            body=self._order_payload(order),
        )
        return self._parse_order_response(order=order, response=response)

    def issue_access_token(self) -> str:
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
            raise KisResponseError("KIS token response did not include a usable access_token.")
        return access_token

    def _price_tr_id(self) -> str:
        return os.getenv("TRADING_SYSTEM_KIS_PRICE_TR_ID", "FHKST01010100")

    def _order_tr_id(self, side: OrderSide) -> str:
        default = "TTTC0802U" if side == OrderSide.BUY else "TTTC0801U"
        return os.getenv("TRADING_SYSTEM_KIS_ORDER_TR_ID", default)

    def _order_headers(self, *, access_token: str, side: OrderSide) -> dict[str, str]:
        return {
            "authorization": f"Bearer {access_token}",
            "appkey": self._credentials.app_key,
            "appsecret": self._credentials.app_secret,
            "tr_id": self._order_tr_id(side),
            "custtype": "P",
            "content-type": "application/json",
        }

    def _order_payload(self, order: OrderRequest) -> dict[str, str]:
        return {
            "CANO": self._credentials.account_number,
            "ACNT_PRDT_CD": self._credentials.product_code,
            "PDNO": order.symbol,
            "ORD_DVSN": "00",
            "ORD_QTY": str(order.quantity),
            "ORD_UNPR": str(order.limit_price or Decimal("0")),
        }

    def _parse_order_response(self, *, order: OrderRequest, response: HttpResponse) -> KisOrderResult:
        result_code = str(response.body.get("rt_cd", ""))
        message = str(response.body.get("msg1", "unknown error"))
        if response.status_code >= 400:
            raise KisHttpError(
                f"KIS order request failed with status={response.status_code}: {message}"
            )
        if result_code and result_code != "0":
            raise KisResponseError(
                "KIS order rejected "
                f"(rt_cd={result_code}, msg_cd={response.body.get('msg_cd', '')}, msg1={message})."
            )

        output = _as_dict(response.body.get("output"), "output")
        order_id = str(output.get("ODNO") or "")
        if not order_id:
            raise KisResponseError("KIS order response field 'ODNO' was missing.")

        filled_quantity = _as_decimal(output.get("ORD_QTY"), "ORD_QTY", default=Decimal("0"))
        fill_price = _as_decimal(
            output.get("ORD_UNPR") or order.limit_price,
            "ORD_UNPR",
            default=Decimal("0"),
        )
        return KisOrderResult(
            order_id=order_id,
            symbol=order.symbol,
            side=order.side,
            requested_quantity=order.quantity,
            filled_quantity=filled_quantity,
            fill_price=fill_price,
            fee=Decimal("0"),
        )


def _as_dict(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise KisResponseError(f"KIS response field '{field_name}' was missing or invalid.")
    return value


def _as_decimal(value: Any, field_name: str, *, default: Decimal | None = None) -> Decimal:
    if value in (None, ""):
        if default is not None:
            return default
        raise KisResponseError(f"KIS response field '{field_name}' was missing.")
    try:
        return Decimal(str(value))
    except Exception as exc:  # pragma: no cover - defensive parser path
        raise KisResponseError(f"KIS response field '{field_name}' was not numeric.") from exc
