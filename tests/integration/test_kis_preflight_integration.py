"""Integration tests for KIS preflight readiness flow."""

from datetime import datetime, timezone
from decimal import Decimal

from trading_system.app.services import PreflightCheckResult, build_services
from trading_system.app.settings import AppSettings


def test_kis_preflight_returns_structured_readiness(monkeypatch) -> None:
    """Full preflight flow returns a structured PreflightCheckResult."""
    monkeypatch.setattr(
        "trading_system.app.services.KisApiClient.from_env",
        lambda: _StubKisClient(),
    )
    monkeypatch.setattr(
        "trading_system.app.services.is_krx_market_open",
        lambda: True,
    )

    settings = AppSettings.from_cli(
        mode="live",
        symbols="005930",
        provider="kis",
        broker="kis",
        live_execution="preflight",
        starting_cash="1000000",
        fee_bps="5",
        trade_quantity="1",
        max_position="10",
        max_notional="100000000",
        max_order_size="5",
    )
    settings.validate()

    services = build_services(settings)
    result = services.preflight_live()

    assert isinstance(result, PreflightCheckResult)
    assert result.ready is True
    assert result.quote_summary is not None
    assert result.quote_summary["symbol"] == "005930"
    assert result.quote_summary["price"] == "70200"
    assert result.quote_summaries == [result.quote_summary]
    assert result.symbol_count == 1
    assert result.reasons == []


def test_kis_preflight_market_closed_blocks_live_mode(monkeypatch) -> None:
    """When market is closed, preflight for live mode is not ready."""
    monkeypatch.setattr(
        "trading_system.app.services.KisApiClient.from_env",
        lambda: _StubKisClient(),
    )
    monkeypatch.setattr(
        "trading_system.app.services.is_krx_market_open",
        lambda: False,
    )

    settings = AppSettings.from_cli(
        mode="live",
        symbols="005930",
        provider="kis",
        broker="kis",
        live_execution="live",
        starting_cash="1000000",
        fee_bps="5",
        trade_quantity="1",
        max_position="10",
        max_notional="100000000",
        max_order_size="5",
    )
    settings.validate()

    services = build_services(settings)
    result = services.preflight_live()

    assert result.ready is False
    assert "market_closed" in result.reasons


def test_kis_preflight_quote_error_blocks_readiness(monkeypatch) -> None:
    """When quote fetch fails, preflight is not ready."""
    monkeypatch.setattr(
        "trading_system.app.services.KisApiClient.from_env",
        lambda: _FailingKisClient(),
    )
    monkeypatch.setattr(
        "trading_system.app.services.is_krx_market_open",
        lambda: True,
    )

    settings = AppSettings.from_cli(
        mode="live",
        symbols="005930",
        provider="kis",
        broker="kis",
        live_execution="preflight",
        starting_cash="1000000",
        fee_bps="5",
        trade_quantity="1",
        max_position="10",
        max_notional="100000000",
        max_order_size="5",
    )
    settings.validate()

    services = build_services(settings)
    result = services.preflight_live()

    assert result.ready is False
    assert any("quote_error" in r for r in result.reasons)


def test_kis_preflight_returns_multi_symbol_readiness(monkeypatch) -> None:
    monkeypatch.setattr(
        "trading_system.app.services.KisApiClient.from_env",
        lambda: _StubKisClient(),
    )
    monkeypatch.setattr(
        "trading_system.app.services.is_krx_market_open",
        lambda: True,
    )

    settings = AppSettings.from_cli(
        mode="live",
        symbols="005930,035720",
        provider="kis",
        broker="kis",
        live_execution="preflight",
        starting_cash="1000000",
        fee_bps="5",
        trade_quantity="1",
        max_position="10",
        max_notional="100000000",
        max_order_size="5",
    )
    settings.validate()

    services = build_services(settings)
    result = services.preflight_live()

    assert result.ready is True
    assert result.symbol_count == 2
    assert result.quote_summary is not None
    assert result.quote_summary["symbol"] == "005930"
    assert result.quote_summaries is not None
    assert [quote["symbol"] for quote in result.quote_summaries] == ["005930", "035720"]


class _StubKisClient:
    def preflight_symbol(self, symbol: str):
        class Quote:
            def __init__(self, s: str) -> None:
                self.symbol = s
                self.price = Decimal("70200")
                self.volume = Decimal("1200")
                self.as_of = datetime(2024, 1, 2, tzinfo=timezone.utc)

        return Quote(symbol)


class _FailingKisClient:
    def preflight_symbol(self, symbol: str):
        raise RuntimeError("KIS API connection failed")
