from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from trading_system.app.loop import LiveTradingLoop
from trading_system.app.services import AppServices
from trading_system.app.settings import AppMode, LiveExecutionMode
from trading_system.core.ops import StructuredLogFormat, StructuredLogger
from trading_system.core.types import MarketBar
from trading_system.data.provider import InMemoryMarketDataProvider
from trading_system.execution.broker import (
    BpsCommissionPolicy,
    BpsSlippagePolicy,
    FixedRatioFillPolicy,
    PolicyBrokerSimulator,
    ResilientBroker,
)
from trading_system.execution.step import TradingContext
from trading_system.portfolio.book import PortfolioBook
from trading_system.risk.limits import RiskLimits
from trading_system.strategy.base import SignalSide, StrategySignal


@dataclass(slots=True)
class BuyFirstBarStrategy:
    name: str = "buy_first_bar"
    _seen: bool = False

    def evaluate(self, bar: MarketBar) -> StrategySignal:
        if self._seen:
            return StrategySignal(side=SignalSide.HOLD, quantity=Decimal("0"), reason="seen")
        self._seen = True
        return StrategySignal(side=SignalSide.BUY, quantity=Decimal("1"), reason=bar.symbol)


def test_live_loop_processes_multiple_symbols_with_isolated_strategies() -> None:
    bars_by_symbol = {
        "BTCUSDT": [_bar("BTCUSDT", "100", 0)],
        "ETHUSDT": [_bar("ETHUSDT", "50", 0)],
    }
    services = AppServices(
        mode=AppMode.LIVE,
        provider="mock",
        broker="paper",
        live_execution=LiveExecutionMode.PAPER,
        strategy=BuyFirstBarStrategy(),
        strategies={
            "BTCUSDT": BuyFirstBarStrategy(),
            "ETHUSDT": BuyFirstBarStrategy(),
        },
        data_provider=InMemoryMarketDataProvider(bars_by_symbol=bars_by_symbol),
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
        symbols=("BTCUSDT", "ETHUSDT"),
        logger=StructuredLogger("test.multi", log_format=StructuredLogFormat.JSON),
    )

    loop = LiveTradingLoop(services=services)
    loop._run_tick(
        context=TradingContext(
            portfolio=services.portfolio,
            risk_limits=services.risk_limits,
            broker=services.broker_simulator,
            logger=services.logger,
            portfolio_risk=services.portfolio_risk,
            runtime_state=loop.runtime,
            marks=loop.runtime.last_marks,
        )
    )

    assert services.portfolio.positions == {
        "BTCUSDT": Decimal("1"),
        "ETHUSDT": Decimal("1"),
    }
    assert services.portfolio.cash == Decimal("850")
    assert loop._last_processed_timestamps.keys() == {"BTCUSDT", "ETHUSDT"}


def _bar(symbol: str, close: str, minute: int) -> MarketBar:
    return MarketBar(
        symbol=symbol,
        timestamp=datetime(2024, 1, 1, 0, minute, tzinfo=timezone.utc),
        open=Decimal(close),
        high=Decimal(close),
        low=Decimal(close),
        close=Decimal(close),
        volume=Decimal("1"),
    )
