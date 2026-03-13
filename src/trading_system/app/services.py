from dataclasses import dataclass

from trading_system.app.sample_data import build_sample_bars
from trading_system.app.settings import AppMode, AppSettings
from trading_system.backtest.engine import BacktestContext, BacktestResult, run_backtest
from trading_system.core.ops import (
    EnvSecretProvider,
    StructuredLogFormat,
    StructuredLogger,
    correlation_scope,
    ensure_logging,
)
from trading_system.data.provider import InMemoryMarketDataProvider, MarketDataProvider
from trading_system.execution.broker import (
    BpsCommissionPolicy,
    BpsSlippagePolicy,
    FixedRatioFillPolicy,
    PolicyBrokerSimulator,
    ResilientBroker,
)
from trading_system.portfolio.book import PortfolioBook
from trading_system.risk.limits import RiskLimits
from trading_system.strategy.base import Strategy
from trading_system.strategy.example import MomentumStrategy


@dataclass(slots=True)
class AppServices:
    mode: AppMode
    strategy: Strategy
    data_provider: MarketDataProvider
    risk_limits: RiskLimits
    broker_simulator: ResilientBroker
    portfolio: PortfolioBook
    symbols: tuple[str, ...]
    logger: StructuredLogger

    def run(self) -> BacktestResult:
        if self.mode != AppMode.BACKTEST:
            raise RuntimeError(f"Unsupported mode '{self.mode}'.")

        symbol = self._single_symbol()
        with correlation_scope():
            bars = self.data_provider.load_bars(symbol)
            context = BacktestContext(
                portfolio=self.portfolio,
                risk_limits=self.risk_limits,
                broker=self.broker_simulator,
                logger=self.logger,
            )
            return run_backtest(bars=bars, strategy=self.strategy, context=context)

    def _single_symbol(self) -> str:
        if len(self.symbols) != 1:
            raise RuntimeError("Current scaffold supports exactly one symbol for backtest mode.")
        return self.symbols[0]


def build_services(settings: AppSettings) -> AppServices:
    if settings.mode != AppMode.BACKTEST:
        raise RuntimeError(f"Mode '{settings.mode}' is not implemented yet.")

    ensure_logging()
    logger = StructuredLogger("trading_system", log_format=StructuredLogFormat.JSON)
    _load_live_api_key_if_present()

    bars_by_symbol = {symbol: build_sample_bars(symbol=symbol) for symbol in settings.symbols}
    return AppServices(
        mode=settings.mode,
        strategy=MomentumStrategy(trade_quantity=settings.backtest.trade_quantity),
        data_provider=InMemoryMarketDataProvider(bars_by_symbol=bars_by_symbol),
        risk_limits=RiskLimits(
            max_position=settings.risk.max_position,
            max_notional=settings.risk.max_notional,
            max_order_size=settings.risk.max_order_size,
        ),
        broker_simulator=ResilientBroker(
            delegate=PolicyBrokerSimulator(
                fill_quantity_policy=FixedRatioFillPolicy(),
                slippage_policy=BpsSlippagePolicy(),
                commission_policy=BpsCommissionPolicy(bps=settings.backtest.fee_bps),
            )
        ),
        portfolio=PortfolioBook(cash=settings.backtest.starting_cash),
        symbols=settings.symbols,
        logger=logger,
    )


def _load_live_api_key_if_present() -> None:
    provider = EnvSecretProvider()
    try:
        provider.get_secret("TRADING_SYSTEM_API_KEY")
    except RuntimeError:
        return
