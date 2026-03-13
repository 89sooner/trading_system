from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from trading_system.backtest.engine import BacktestContext, run_backtest
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


def test_run_backtest_marks_equity_across_multiple_symbols() -> None:
    context = BacktestContext(
        portfolio=PortfolioBook(cash=Decimal("1000"), positions={"ETHUSDT": Decimal("3")}),
        risk_limits=_limits(),
        broker=_broker(),
    )
    strategy = StubStrategy(
        signals=[
            StrategySignal(side=SignalSide.BUY, quantity=Decimal("1"), reason="btc_entry"),
            StrategySignal(side=SignalSide.HOLD, quantity=Decimal("0"), reason="eth_mark"),
        ]
    )
    bars = [
        MarketBar(
            symbol="BTCUSDT",
            timestamp=datetime(2024, 1, 1, 0, 0, 0),
            open=Decimal("100"),
            high=Decimal("100"),
            low=Decimal("100"),
            close=Decimal("100"),
            volume=Decimal("1"),
        ),
        MarketBar(
            symbol="ETHUSDT",
            timestamp=datetime(2024, 1, 1, 0, 0, 1),
            open=Decimal("50"),
            high=Decimal("50"),
            low=Decimal("50"),
            close=Decimal("50"),
            volume=Decimal("1"),
        ),
    ]

    result = run_backtest(bars, strategy, context)

    assert result.equity_curve == [Decimal("1000"), Decimal("1150")]


def test_run_backtest_tracks_fees_inside_portfolio_book() -> None:
    context = BacktestContext(
        portfolio=PortfolioBook(cash=Decimal("1000")),
        risk_limits=_limits(),
        broker=_broker(commission_bps=Decimal("10")),
    )
    strategy = StubStrategy(
        signals=[StrategySignal(side=SignalSide.BUY, quantity=Decimal("2"), reason="entry")]
    )

    result = run_backtest(_bars([Decimal("100")]), strategy, context)

    assert result.final_portfolio.fees_paid["BTCUSDT"] == Decimal("0.2")
    assert result.final_portfolio.total_fees_paid() == Decimal("0.2")


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


def _bars(closes: list[Decimal]) -> list[MarketBar]:
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
