from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from trading_system.app.sample_data import build_sample_bars
from trading_system.app.settings import AppMode, AppSettings
from trading_system.backtest.engine import BacktestContext, BacktestResult, run_backtest
from trading_system.core.types import MarketBar
from trading_system.portfolio.book import PortfolioBook
from trading_system.risk.limits import RiskLimits
from trading_system.strategy.base import Strategy
from trading_system.strategy.example import MomentumStrategy


class MockMarketDataProvider:
    def __init__(self, symbols: tuple[str, ...]) -> None:
        self._bars_by_symbol: dict[str, list[MarketBar]] = {
            symbol: build_sample_bars(symbol=symbol) for symbol in symbols
        }

    def load_bars(self, symbol: str) -> Iterable[MarketBar]:
        return list(self._bars_by_symbol[symbol])


@dataclass(slots=True)
class PaperExecutionService:
    broker: str


@dataclass(slots=True)
class AppServices:
    mode: AppMode
    strategy: Strategy
    data_provider: MockMarketDataProvider
    risk_limits: RiskLimits
    execution: PaperExecutionService
    portfolio: PortfolioBook
    fee_bps: Decimal
    symbols: tuple[str, ...]

    def run(self) -> BacktestResult:
        if self.mode != AppMode.BACKTEST:
            raise RuntimeError(f"Unsupported mode '{self.mode}'.")

        symbol = self._single_symbol()
        bars = self.data_provider.load_bars(symbol)
        context = BacktestContext(
            portfolio=self.portfolio,
            risk_limits=self.risk_limits,
            fee_bps=self.fee_bps,
        )
        return run_backtest(bars=bars, strategy=self.strategy, context=context)

    def _single_symbol(self) -> str:
        if len(self.symbols) != 1:
            raise RuntimeError("Current scaffold supports exactly one symbol for backtest mode.")
        return self.symbols[0]


def build_services(settings: AppSettings) -> AppServices:
    if settings.mode != AppMode.BACKTEST:
        raise RuntimeError(f"Mode '{settings.mode}' is not implemented yet.")

    return AppServices(
        mode=settings.mode,
        strategy=MomentumStrategy(trade_quantity=settings.backtest.trade_quantity),
        data_provider=MockMarketDataProvider(symbols=settings.symbols),
        risk_limits=RiskLimits(
            max_position=settings.risk.max_position,
            max_notional=settings.risk.max_notional,
            max_order_size=settings.risk.max_order_size,
        ),
        execution=PaperExecutionService(broker=settings.broker),
        portfolio=PortfolioBook(cash=settings.backtest.starting_cash),
        fee_bps=settings.backtest.fee_bps,
        symbols=settings.symbols,
    )
