from datetime import datetime, timezone
from decimal import Decimal

from trading_system.core.ops import StructuredLogFormat, StructuredLogger
from trading_system.core.types import MarketBar
from trading_system.execution.adapters import signal_to_order_request
from trading_system.execution.broker import (
    BpsCommissionPolicy,
    BpsSlippagePolicy,
    FillStatus,
    FixedRatioFillPolicy,
    PolicyBrokerSimulator,
)
from trading_system.execution.step import TradingContext, execute_trading_step
from trading_system.portfolio.book import PortfolioBook
from trading_system.risk.limits import RiskLimits
from trading_system.strategy.base import SignalSide, StrategySignal


def test_signal_to_order_request_maps_buy_signal() -> None:
    signal = StrategySignal(side=SignalSide.BUY, quantity=Decimal("1.2"), reason="entry")

    order = signal_to_order_request("BTCUSDT", signal)

    assert order is not None
    assert order.symbol == "BTCUSDT"
    assert order.side.value == "buy"
    assert order.quantity == Decimal("1.2")


def test_signal_to_order_request_returns_none_for_hold() -> None:
    signal = StrategySignal(side=SignalSide.HOLD, quantity=Decimal("0"), reason="wait")

    order = signal_to_order_request("BTCUSDT", signal)

    assert order is None


def test_policy_broker_simulator_returns_partial_fill_event() -> None:
    broker = PolicyBrokerSimulator(
        fill_quantity_policy=FixedRatioFillPolicy(fill_ratio=Decimal("0.25")),
        slippage_policy=BpsSlippagePolicy(bps=Decimal("10")),
        commission_policy=BpsCommissionPolicy(bps=Decimal("5")),
    )

    fill = broker.submit_order(_buy_signal_order(), _bar())

    assert fill.status == FillStatus.PARTIALLY_FILLED
    assert fill.filled_quantity == Decimal("0.25")
    assert fill.fill_price == Decimal("100.10")
    assert fill.fee == Decimal("0.0125125")


def test_policy_broker_simulator_returns_unfilled_event() -> None:
    broker = PolicyBrokerSimulator(
        fill_quantity_policy=FixedRatioFillPolicy(fill_ratio=Decimal("0")),
        slippage_policy=BpsSlippagePolicy(),
        commission_policy=BpsCommissionPolicy(),
    )

    fill = broker.submit_order(_buy_signal_order(), _bar())

    assert fill.status == FillStatus.UNFILLED
    assert fill.filled_quantity == Decimal("0")
    assert fill.fee == Decimal("0")


def test_accepted_but_unfilled_order_does_not_change_portfolio() -> None:
    broker = PolicyBrokerSimulator(
        fill_quantity_policy=FixedRatioFillPolicy(fill_ratio=Decimal("0")),
        slippage_policy=BpsSlippagePolicy(),
        commission_policy=BpsCommissionPolicy(),
    )
    portfolio = PortfolioBook(
        cash=Decimal("10000"),
        positions={},
        average_costs={},
    )
    risk_limits = RiskLimits(
        max_position=Decimal("10"),
        max_notional=Decimal("1000000"),
        max_order_size=Decimal("5"),
    )
    logger = StructuredLogger("test.step.unfilled", log_format=StructuredLogFormat.JSON)
    context = TradingContext(
        portfolio=portfolio, risk_limits=risk_limits, broker=broker, logger=logger
    )

    class _BuyStrategy:
        name = "test_buy"

        def evaluate(self, bar):  # noqa: ANN001
            return StrategySignal(side=SignalSide.BUY, quantity=Decimal("1"), reason="entry")

    execute_trading_step(_bar(), _BuyStrategy(), context)

    assert portfolio.positions == {}


def _bar() -> MarketBar:
    return MarketBar(
        symbol="BTCUSDT",
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=Decimal("100"),
        high=Decimal("100"),
        low=Decimal("100"),
        close=Decimal("100"),
        volume=Decimal("1"),
    )


def _buy_signal_order():
    signal = StrategySignal(side=SignalSide.BUY, quantity=Decimal("1"), reason="entry")
    order = signal_to_order_request("BTCUSDT", signal)
    assert order is not None
    return order
