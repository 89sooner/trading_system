"""Unit tests for multi-symbol live loop orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from trading_system.app.loop import LiveTradingLoop
from trading_system.app.state import AppRunnerState
from trading_system.core.types import MarketBar


def _make_bar(symbol: str, close: str, ts: datetime | None = None) -> MarketBar:
    ts = ts or datetime(2025, 1, 1, tzinfo=timezone.utc)
    return MarketBar(
        symbol=symbol,
        timestamp=ts,
        open=Decimal(close),
        high=Decimal(close),
        low=Decimal(close),
        close=Decimal(close),
        volume=Decimal("1"),
    )


def _make_services(symbols: tuple[str, ...]) -> MagicMock:
    services = MagicMock()
    services.symbols = symbols
    services.portfolio_repository = None

    # Each call to load_bars returns one bar for the requested symbol
    def _load_bars(symbol: str):
        return [_make_bar(symbol, "100")]

    services.data_provider.load_bars.side_effect = _load_bars

    from trading_system.strategy.base import SignalSide, StrategySignal

    services.strategy.evaluate.return_value = StrategySignal(
        side=SignalSide.HOLD, quantity=Decimal("0"), reason="hold"
    )
    services.logger = MagicMock()
    return services


class TestMultiSymbolTick:
    def test_both_symbols_processed_each_tick(self) -> None:
        """Each symbol should be loaded and evaluated every tick."""
        symbols = ("BTCUSDT", "ETHUSDT")
        services = _make_services(symbols)

        loop = LiveTradingLoop(services=services, poll_interval=1)
        loop.state = AppRunnerState.RUNNING

        from trading_system.execution.step import TradingContext
        from trading_system.portfolio.book import PortfolioBook
        from trading_system.risk.limits import RiskLimits

        context = TradingContext(
            portfolio=PortfolioBook(cash=Decimal("10000")),
            risk_limits=RiskLimits(
                max_position=Decimal("10"),
                max_notional=Decimal("100000"),
                max_order_size=Decimal("1"),
            ),
            broker=MagicMock(),
        )

        loop._run_tick(context)  # noqa: SLF001

        # data_provider.load_bars should be called once per symbol
        calls = [call.args[0] for call in services.data_provider.load_bars.call_args_list]
        assert "BTCUSDT" in calls
        assert "ETHUSDT" in calls

    def test_per_symbol_timestamp_tracked_independently(self) -> None:
        """Timestamps are tracked per symbol and old bars are not re-processed."""
        from datetime import timedelta

        symbols = ("AAPL", "TSLA")
        services = _make_services(symbols)

        ts_old = datetime(2025, 1, 1, tzinfo=timezone.utc)
        ts_new = ts_old + timedelta(hours=1)

        # First tick: one bar per symbol at ts_old
        services.data_provider.load_bars.side_effect = lambda s: [_make_bar(s, "100", ts_old)]

        loop = LiveTradingLoop(services=services)
        from trading_system.execution.step import TradingContext
        from trading_system.portfolio.book import PortfolioBook
        from trading_system.risk.limits import RiskLimits

        context = TradingContext(
            portfolio=PortfolioBook(cash=Decimal("10000")),
            risk_limits=RiskLimits(
                max_position=Decimal("10"),
                max_notional=Decimal("100000"),
                max_order_size=Decimal("1"),
            ),
            broker=MagicMock(),
        )

        loop._run_tick(context)  # noqa: SLF001
        assert "AAPL" in loop._last_processed_timestamps  # noqa: SLF001
        assert "TSLA" in loop._last_processed_timestamps  # noqa: SLF001

        # Second tick: same old bar — should NOT be re-processed
        evaluate_call_count_before = services.strategy.evaluate.call_count
        loop._run_tick(context)  # noqa: SLF001
        # No new evaluate calls since same timestamp
        assert services.strategy.evaluate.call_count == evaluate_call_count_before

        # Third tick: a new bar — should be processed
        services.data_provider.load_bars.side_effect = lambda s: [_make_bar(s, "105", ts_new)]
        loop._run_tick(context)  # noqa: SLF001
        assert services.strategy.evaluate.call_count > evaluate_call_count_before
