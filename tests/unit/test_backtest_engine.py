import json
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from trading_system.backtest.engine import BacktestContext, run_backtest
from trading_system.core.ops import StructuredLogFormat, StructuredLogger
from trading_system.core.types import MarketBar
from trading_system.execution.broker import (
    BpsCommissionPolicy,
    BpsSlippagePolicy,
    FixedRatioFillPolicy,
    PolicyBrokerSimulator,
)
from trading_system.portfolio.book import PortfolioBook
from trading_system.risk.limits import RiskLimits
from trading_system.strategy.base import SignalSide, StrategySignal


@dataclass(slots=True)
class StubStrategy:
    signals: list[StrategySignal]
    name: str = "stub"
    _index: int = 0

    def evaluate(self, bar: MarketBar) -> StrategySignal:
        signal = self.signals[self._index]
        self._index += 1
        return signal


def test_run_backtest_executes_buy_at_close_and_records_return() -> None:
    context = BacktestContext(
        portfolio=PortfolioBook(cash=Decimal("1000")),
        risk_limits=_limits(),
        broker=_broker(),
    )
    strategy = StubStrategy(
        signals=[
            StrategySignal(side=SignalSide.BUY, quantity=Decimal("2"), reason="entry"),
            StrategySignal(side=SignalSide.HOLD, quantity=Decimal("0"), reason="hold"),
        ]
    )

    result = run_backtest(_bars([Decimal("100"), Decimal("110")]), strategy, context)

    assert result.processed_bars == 2
    assert result.executed_trades == 1
    assert result.rejected_signals == 0
    assert result.final_portfolio.positions["BTCUSDT"] == Decimal("2")
    assert result.final_portfolio.cash == Decimal("800")
    assert result.equity_curve == [Decimal("1000"), Decimal("1020")]
    assert result.total_return == Decimal("0.02")


def test_run_backtest_executes_sell_using_negative_signed_quantity() -> None:
    context = BacktestContext(
        portfolio=PortfolioBook(
            cash=Decimal("500"),
            positions={"BTCUSDT": Decimal("2")},
        ),
        risk_limits=_limits(),
        broker=_broker(),
    )
    strategy = StubStrategy(
        signals=[StrategySignal(side=SignalSide.SELL, quantity=Decimal("1.5"), reason="trim")]
    )

    result = run_backtest(_bars([Decimal("100")]), strategy, context)

    assert result.executed_trades == 1
    assert result.final_portfolio.positions["BTCUSDT"] == Decimal("0.5")
    assert result.final_portfolio.cash == Decimal("650")
    assert result.equity_curve == [Decimal("700")]


def test_run_backtest_rejects_signal_when_risk_limits_fail() -> None:
    context = BacktestContext(
        portfolio=PortfolioBook(cash=Decimal("1000")),
        risk_limits=RiskLimits(
            max_position=Decimal("1"),
            max_notional=Decimal("100000"),
            max_order_size=Decimal("0.5"),
        ),
        broker=_broker(),
    )
    strategy = StubStrategy(
        signals=[StrategySignal(side=SignalSide.BUY, quantity=Decimal("1"), reason="too_big")]
    )

    result = run_backtest(_bars([Decimal("100")]), strategy, context)

    assert result.executed_trades == 0
    assert result.rejected_signals == 1
    assert result.final_portfolio.positions == {}
    assert result.final_portfolio.cash == Decimal("1000")
    assert result.equity_curve == [Decimal("1000")]


def test_run_backtest_applies_commission_fee() -> None:
    context = BacktestContext(
        portfolio=PortfolioBook(cash=Decimal("1000")),
        risk_limits=_limits(),
        broker=_broker(commission_bps=Decimal("10")),
    )
    strategy = StubStrategy(
        signals=[StrategySignal(side=SignalSide.BUY, quantity=Decimal("2"), reason="entry")]
    )

    result = run_backtest(_bars([Decimal("100")]), strategy, context)

    assert result.executed_trades == 1
    assert result.final_portfolio.cash == Decimal("799.8")
    assert result.equity_curve == [Decimal("999.8")]


def test_run_backtest_supports_partial_fill_and_unfilled_order() -> None:
    partial_context = BacktestContext(
        portfolio=PortfolioBook(cash=Decimal("1000")),
        risk_limits=_limits(),
        broker=_broker(fill_ratio=Decimal("0.5")),
    )
    partial_result = run_backtest(
        _bars([Decimal("100")]),
        StubStrategy(
            [StrategySignal(side=SignalSide.BUY, quantity=Decimal("2"), reason="partial")]
        ),
        partial_context,
    )

    assert partial_result.executed_trades == 1
    assert partial_result.final_portfolio.positions["BTCUSDT"] == Decimal("1")
    assert partial_result.final_portfolio.cash == Decimal("900")

    unfilled_context = BacktestContext(
        portfolio=PortfolioBook(cash=Decimal("1000")),
        risk_limits=_limits(),
        broker=_broker(fill_ratio=Decimal("0")),
    )
    unfilled_result = run_backtest(
        _bars([Decimal("100")]),
        StubStrategy(
            [StrategySignal(side=SignalSide.BUY, quantity=Decimal("2"), reason="no_fill")]
        ),
        unfilled_context,
    )

    assert unfilled_result.executed_trades == 0
    assert unfilled_result.final_portfolio.positions == {}
    assert unfilled_result.final_portfolio.cash == Decimal("1000")


def test_run_backtest_applies_slippage_to_fill_price() -> None:
    context = BacktestContext(
        portfolio=PortfolioBook(cash=Decimal("1000")),
        risk_limits=_limits(),
        broker=_broker(slippage_bps=Decimal("100")),
    )
    strategy = StubStrategy(
        signals=[StrategySignal(side=SignalSide.BUY, quantity=Decimal("1"), reason="slippage")]
    )

    result = run_backtest(_bars([Decimal("100")]), strategy, context)

    assert result.final_portfolio.cash == Decimal("899")
    assert result.equity_curve == [Decimal("999")]




def _limits() -> RiskLimits:
    return RiskLimits(
        max_position=Decimal("10"),
        max_notional=Decimal("100000"),
        max_order_size=Decimal("10"),
    )


def _broker(
    fill_ratio: Decimal = Decimal("1"),
    slippage_bps: Decimal = Decimal("0"),
    commission_bps: Decimal = Decimal("0"),
) -> PolicyBrokerSimulator:
    return PolicyBrokerSimulator(
        fill_quantity_policy=FixedRatioFillPolicy(fill_ratio=fill_ratio),
        slippage_policy=BpsSlippagePolicy(bps=slippage_bps),
        commission_policy=BpsCommissionPolicy(bps=commission_bps),
    )


def _bars(closes: Iterable[Decimal]) -> list[MarketBar]:
    return [
        MarketBar(
            symbol="BTCUSDT",
            timestamp=datetime(2024, 1, 1, 0, 0, index),
            open=close,
            high=close,
            low=close,
            close=close,
            volume=Decimal("1"),
        )
        for index, close in enumerate(closes)
    ]
