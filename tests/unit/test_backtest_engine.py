from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from trading_system.backtest.engine import BacktestContext, run_backtest
from trading_system.core.types import MarketBar
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
        fee_bps=Decimal("0"),
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
        fee_bps=Decimal("0"),
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
        fee_bps=Decimal("0"),
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


def test_run_backtest_applies_fee_bps_to_cash() -> None:
    context = BacktestContext(
        portfolio=PortfolioBook(cash=Decimal("1000")),
        risk_limits=_limits(),
        fee_bps=Decimal("10"),
    )
    strategy = StubStrategy(
        signals=[StrategySignal(side=SignalSide.BUY, quantity=Decimal("2"), reason="entry")]
    )

    result = run_backtest(_bars([Decimal("100")]), strategy, context)

    assert result.executed_trades == 1
    assert result.final_portfolio.cash == Decimal("799.8")
    assert result.equity_curve == [Decimal("999.8")]


def _limits() -> RiskLimits:
    return RiskLimits(
        max_position=Decimal("10"),
        max_notional=Decimal("100000"),
        max_order_size=Decimal("10"),
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
