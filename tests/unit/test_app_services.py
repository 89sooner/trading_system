from datetime import datetime, timezone
from decimal import Decimal

import pytest

from trading_system.app.services import build_services
from trading_system.app.settings import AppSettings
from trading_system.execution.kis_adapter import KisBrokerAdapter
from trading_system.execution.orders import OrderSide
from trading_system.integrations.kis import KisOrderResult


def test_build_services_uses_csv_provider_for_domestic_symbol(
    tmp_path, monkeypatch
) -> None:
    csv_path = tmp_path / "005930.csv"
    csv_path.write_text(
        "timestamp,open,high,low,close,volume\n"
        "2024-01-02T00:00:00+00:00,70000,70500,69900,70400,1000\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("TRADING_SYSTEM_CSV_DIR", str(tmp_path))

    settings = AppSettings.from_cli(
        mode="backtest",
        symbols="005930",
        provider="csv",
        broker="paper",
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
    bars = list(services.data_provider.load_bars("005930"))

    assert bars[0].symbol == "005930"
    assert bars[0].close == Decimal("70400")
    assert bars[0].timestamp == datetime(2024, 1, 2, tzinfo=timezone.utc)


def test_build_services_raises_clear_error_when_csv_file_missing(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("TRADING_SYSTEM_CSV_DIR", str(tmp_path))

    settings = AppSettings.from_cli(
        mode="backtest",
        symbols="005930",
        provider="csv",
        broker="paper",
        live_execution="preflight",
        starting_cash="1000000",
        fee_bps="5",
        trade_quantity="1",
        max_position="10",
        max_notional="100000000",
        max_order_size="5",
    )
    settings.validate()

    with pytest.raises(RuntimeError, match="missing: 005930"):
        build_services(settings)


def test_live_mode_paper_execution_runs_without_order_submission_error(
    monkeypatch,
) -> None:
    monkeypatch.setenv("TRADING_SYSTEM_API_KEY", "dummy-key")

    settings = AppSettings.from_cli(
        mode="live",
        symbols="BTCUSDT",
        provider="mock",
        broker="paper",
        live_execution="paper",
        starting_cash="10000",
        fee_bps="5",
        trade_quantity="0.1",
        max_position="1",
        max_notional="100000",
        max_order_size="0.25",
    )
    settings.validate()

    import time

    def mock_sleep(_):
        raise KeyboardInterrupt()

    monkeypatch.setattr(time, "sleep", mock_sleep)

    services = build_services(settings)
    services.run_live_paper()


def test_live_mode_kis_preflight_uses_kis_quote(monkeypatch) -> None:
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

    assert result.ready is True
    assert result.quote_summary is not None
    assert result.quote_summary["symbol"] == "005930"
    assert result.quote_summary["price"] == "70200"


def test_live_preflight_supports_multi_symbol(monkeypatch) -> None:
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

    # Single-symbol preflight for first symbol
    assert result.ready is True
    assert result.quote_summary is not None
    assert result.quote_summary["symbol"] == "005930"


def test_live_preflight_no_broker_check_multi_symbol(monkeypatch) -> None:
    """When no broker-specific preflight exists, multi-symbol passes without error."""
    monkeypatch.setenv("TRADING_SYSTEM_API_KEY", "test-key")

    settings = AppSettings.from_cli(
        mode="live",
        symbols="BTCUSDT,ETHUSDT",
        provider="mock",
        broker="paper",
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
    assert result.message == "Live mode preflight passed (no orders were submitted)."


def test_build_services_uses_kis_broker_adapter_when_broker_is_kis(monkeypatch) -> None:
    monkeypatch.setattr(
        "trading_system.app.services.KisApiClient.from_env",
        lambda: _StubKisClient(),
    )

    settings = AppSettings.from_cli(
        mode="live",
        symbols="005930",
        provider="mock",
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

    assert isinstance(services.broker_simulator.delegate, KisBrokerAdapter)


def test_live_execution_requires_opt_in_flag(monkeypatch) -> None:
    monkeypatch.setattr(
        "trading_system.app.services.KisApiClient.from_env",
        lambda: _StubKisClient(),
    )
    monkeypatch.setenv("TRADING_SYSTEM_ENABLE_LIVE_ORDERS", "false")

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

    with pytest.raises(RuntimeError, match="TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true"):
        services.run_live_execution()


def test_live_execution_runs_when_opted_in(monkeypatch) -> None:
    monkeypatch.setattr(
        "trading_system.app.services.KisApiClient.from_env",
        lambda: _StubKisClient(),
    )
    monkeypatch.setattr(
        "trading_system.app.services.is_krx_market_open",
        lambda: True,
    )
    monkeypatch.setenv("TRADING_SYSTEM_ENABLE_LIVE_ORDERS", "true")

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

    import time

    def mock_sleep(_):
        raise KeyboardInterrupt()

    monkeypatch.setattr(time, "sleep", mock_sleep)

    services = build_services(settings)
    services.run_live_execution()


def test_live_execution_can_submit_order_with_moving_quotes(monkeypatch, tmp_path) -> None:
    client = _MovingQuoteKisClient()
    monkeypatch.setattr(
        "trading_system.app.services.KisApiClient.from_env",
        lambda: client,
    )
    monkeypatch.setattr(
        "trading_system.app.services.is_krx_market_open",
        lambda: True,
    )
    monkeypatch.setenv("TRADING_SYSTEM_ENABLE_LIVE_ORDERS", "true")
    monkeypatch.setenv("TRADING_SYSTEM_LIVE_BAR_SAMPLES", "2")
    monkeypatch.setenv("TRADING_SYSTEM_PORTFOLIO_DIR", str(tmp_path))

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

    import time

    def mock_sleep(_):
        raise KeyboardInterrupt()

    monkeypatch.setattr(time, "sleep", mock_sleep)

    services = build_services(settings)
    services.run_live_execution()

    assert client.order_requests == 1


def test_live_execution_blocked_outside_market_hours(monkeypatch) -> None:
    monkeypatch.setattr(
        "trading_system.app.services.KisApiClient.from_env",
        lambda: _StubKisClient(),
    )
    monkeypatch.setattr(
        "trading_system.app.services.is_krx_market_open",
        lambda: False,
    )
    monkeypatch.setenv("TRADING_SYSTEM_ENABLE_LIVE_ORDERS", "true")

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
    with pytest.raises(RuntimeError, match="KRX market hours"):
        services.run_live_execution()


def test_live_preflight_includes_market_closed_reason(monkeypatch) -> None:
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

    assert "market_closed" in result.reasons


def test_live_execution_rejects_invalid_live_sample_env(monkeypatch) -> None:
    monkeypatch.setattr(
        "trading_system.app.services.KisApiClient.from_env",
        lambda: _StubKisClient(),
    )
    monkeypatch.setenv("TRADING_SYSTEM_ENABLE_LIVE_ORDERS", "true")
    monkeypatch.setenv("TRADING_SYSTEM_LIVE_BAR_SAMPLES", "invalid")

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

    with pytest.raises(RuntimeError, match="TRADING_SYSTEM_LIVE_BAR_SAMPLES"):
        build_services(settings)


class _StubKisClient:
    def preflight_symbol(self, symbol: str):
        class Quote:
            def __init__(self, quote_symbol: str) -> None:
                self.symbol = quote_symbol
                self.price = Decimal("70200")
                self.volume = Decimal("1200")
                self.as_of = datetime(2024, 1, 2, tzinfo=timezone.utc)

        return Quote(symbol)


class _MovingQuoteKisClient:
    def __init__(self) -> None:
        self._price_sequence = iter([Decimal("70200"), Decimal("70300")])
        self.order_requests = 0
        self.preflight_calls = 0

    def preflight_symbol(self, symbol: str):
        from datetime import timedelta

        self.preflight_calls += 1
        current_time = datetime(2024, 1, 2, tzinfo=timezone.utc) + timedelta(
            seconds=self.preflight_calls
        )

        class Quote:
            def __init__(self, quote_symbol: str, price: Decimal) -> None:
                self.symbol = quote_symbol
                self.price = price
                self.volume = Decimal("1500")
                self.as_of = current_time

        return Quote(symbol, next(self._price_sequence))

    def submit_order(self, order):
        self.order_requests += 1
        return KisOrderResult(
            order_id="live-order-1",
            symbol=order.symbol,
            side=OrderSide.BUY,
            requested_quantity=order.quantity,
            filled_quantity=order.quantity,
            fill_price=Decimal("70300"),
            fee=Decimal("0"),
        )
