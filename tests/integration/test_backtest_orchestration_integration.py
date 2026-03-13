from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from trading_system.app.services import AppServices
from trading_system.app.settings import AppMode
from trading_system.core.ops import (
    CircuitBreakerPolicy,
    RetryPolicy,
    StructuredLogFormat,
    StructuredLogger,
    TimeoutPolicy,
)
from trading_system.core.types import MarketBar
from trading_system.data.provider import InMemoryMarketDataProvider
from trading_system.execution.broker import (
    BpsCommissionPolicy,
    BpsSlippagePolicy,
    FillEvent,
    FillStatus,
    FixedRatioFillPolicy,
    PolicyBrokerSimulator,
    ResilientBroker,
)
from trading_system.execution.orders import OrderRequest
from trading_system.portfolio.book import PortfolioBook
from trading_system.risk.limits import RiskLimits
from trading_system.strategy.base import SignalSide, StrategySignal


@dataclass(slots=True)
class SequenceStrategy:
    signals: list[StrategySignal]
    name: str = "sequence"
    _index: int = 0

    def evaluate(self, bar: MarketBar) -> StrategySignal:
        del bar
        signal = self.signals[self._index]
        self._index += 1
        return signal


@dataclass(slots=True)
class FailingProvider:
    error: Exception

    def load_bars(self, symbol: str):
        del symbol
        raise self.error


@dataclass(slots=True)
class OSErrorBroker:
    def submit_order(self, order: OrderRequest, bar: MarketBar) -> FillEvent:
        del order, bar
        raise OSError("broker transport unavailable")


@dataclass(slots=True)
class DelayedBroker:
    delay_seconds: float

    def submit_order(self, order: OrderRequest, bar: MarketBar) -> FillEvent:
        time.sleep(self.delay_seconds)
        return FillEvent(
            symbol=order.symbol,
            side=order.side,
            requested_quantity=order.quantity,
            filled_quantity=order.quantity,
            fill_price=bar.close,
            fee=Decimal("0"),
            status=FillStatus.FILLED,
        )


@pytest.mark.smoke
def test_backtest_orchestration_pipeline_happy_path_and_determinism() -> None:
    result_a = _run_happy_path_backtest()
    result_b = _run_happy_path_backtest()

    assert result_a.processed_bars == 3
    assert result_a.executed_trades == 2
    assert result_a.rejected_signals == 0
    assert result_a.final_portfolio.cash == Decimal("990")
    assert result_a.final_portfolio.positions == {}
    assert result_a.equity_curve == [Decimal("1000"), Decimal("1010"), Decimal("990")]
    assert result_a.total_return == Decimal("-0.01")

    assert _snapshot(result_a) == _snapshot(result_b)


def test_backtest_orchestration_rejects_signal_when_risk_disallows_order() -> None:
    services = _build_services(
        strategy=SequenceStrategy(
            signals=[StrategySignal(side=SignalSide.BUY, quantity=Decimal("2"), reason="entry")]
        ),
        risk_limits=RiskLimits(
            max_position=Decimal("1"),
            max_notional=Decimal("100000"),
            max_order_size=Decimal("1"),
        ),
        bars=[_bar(Decimal("100"), 0)],
    )

    result = services.run()

    assert result.executed_trades == 0
    assert result.rejected_signals == 1
    assert result.final_portfolio.cash == Decimal("1000")
    assert result.final_portfolio.positions == {}


@pytest.mark.extended
def test_backtest_orchestration_propagates_provider_error() -> None:
    services = AppServices(
        mode=AppMode.BACKTEST,
        strategy=SequenceStrategy([]),
        data_provider=FailingProvider(ValueError("provider disconnected")),
        risk_limits=RiskLimits(
            max_position=Decimal("10"),
            max_notional=Decimal("100000"),
            max_order_size=Decimal("10"),
        ),
        broker_simulator=ResilientBroker(
            delegate=PolicyBrokerSimulator(
                fill_quantity_policy=FixedRatioFillPolicy(),
                slippage_policy=BpsSlippagePolicy(),
                commission_policy=BpsCommissionPolicy(),
            )
        ),
        portfolio=PortfolioBook(cash=Decimal("1000")),
        symbols=("BTCUSDT",),
        logger=StructuredLogger("test", log_format=StructuredLogFormat.JSON),
    )

    with pytest.raises(ValueError, match="provider disconnected"):
        services.run()


@pytest.mark.extended
@pytest.mark.parametrize(
    ("delegate", "timeout_seconds", "cause_type"),
    [
        (OSErrorBroker(), 0.1, OSError),
        (DelayedBroker(delay_seconds=0.01), 0.001, TimeoutError),
    ],
)
def test_backtest_orchestration_fails_on_broker_errors(
    delegate,
    timeout_seconds: float,
    cause_type: type[Exception],
) -> None:
    services = _build_services(
        strategy=SequenceStrategy(
            signals=[StrategySignal(side=SignalSide.BUY, quantity=Decimal("1"), reason="entry")]
        ),
        risk_limits=RiskLimits(
            max_position=Decimal("10"),
            max_notional=Decimal("100000"),
            max_order_size=Decimal("10"),
        ),
        bars=[_bar(Decimal("100"), 0)],
        broker=ResilientBroker(
            delegate=delegate,
            retry_policy=RetryPolicy(max_attempts=1, backoff_seconds=0),
            timeout_policy=TimeoutPolicy(timeout_seconds=timeout_seconds),
            circuit_breaker_policy=CircuitBreakerPolicy(
                failure_threshold=1,
                reset_timeout_seconds=1,
            ),
        ),
    )

    with pytest.raises(RuntimeError, match="failed after 1 attempts") as exc_info:
        services.run()

    assert isinstance(exc_info.value.__cause__, cause_type)


def _run_happy_path_backtest():
    services = _build_services(
        strategy=SequenceStrategy(
            signals=[
                StrategySignal(side=SignalSide.BUY, quantity=Decimal("1"), reason="entry"),
                StrategySignal(side=SignalSide.HOLD, quantity=Decimal("0"), reason="hold"),
                StrategySignal(side=SignalSide.SELL, quantity=Decimal("1"), reason="exit"),
            ]
        ),
        risk_limits=RiskLimits(
            max_position=Decimal("10"),
            max_notional=Decimal("100000"),
            max_order_size=Decimal("10"),
        ),
        bars=[_bar(Decimal("100"), 0), _bar(Decimal("110"), 1), _bar(Decimal("90"), 2)],
    )
    return services.run()


def _build_services(
    strategy: SequenceStrategy,
    risk_limits: RiskLimits,
    bars: list[MarketBar],
    broker: ResilientBroker | None = None,
) -> AppServices:
    return AppServices(
        mode=AppMode.BACKTEST,
        strategy=strategy,
        data_provider=InMemoryMarketDataProvider(bars_by_symbol={"BTCUSDT": bars}),
        risk_limits=risk_limits,
        broker_simulator=broker
        or ResilientBroker(
            delegate=PolicyBrokerSimulator(
                fill_quantity_policy=FixedRatioFillPolicy(),
                slippage_policy=BpsSlippagePolicy(),
                commission_policy=BpsCommissionPolicy(),
            )
        ),
        portfolio=PortfolioBook(cash=Decimal("1000")),
        symbols=("BTCUSDT",),
        logger=StructuredLogger("test", log_format=StructuredLogFormat.JSON),
    )


def _snapshot(result) -> tuple[Decimal, dict[str, Decimal], list[Decimal], Decimal]:
    return (
        result.final_portfolio.cash,
        dict(result.final_portfolio.positions),
        list(result.equity_curve),
        result.total_return,
    )


def _bar(close: Decimal, minute: int) -> MarketBar:
    return MarketBar(
        symbol="BTCUSDT",
        timestamp=datetime(2024, 1, 1, 0, minute, tzinfo=timezone.utc),
        open=close,
        high=close,
        low=close,
        close=close,
        volume=Decimal("1"),
    )
