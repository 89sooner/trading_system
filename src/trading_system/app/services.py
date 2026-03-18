import os
from dataclasses import dataclass
from pathlib import Path

from trading_system.app.sample_data import build_sample_bars
from trading_system.app.settings import AppMode, AppSettings
from trading_system.backtest.engine import BacktestContext, BacktestResult, run_backtest
from trading_system.core.ops import (
    EnvSecretProvider,
    StructuredLogFormat,
    StructuredLogger,
    ensure_logging,
)
from trading_system.data.provider import (
    CsvMarketDataProvider,
    InMemoryMarketDataProvider,
    MarketDataProvider,
)
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

        symbol = self._single_symbol(mode_name="backtest")
        bars = self.data_provider.load_bars(symbol)
        context = BacktestContext(
            portfolio=self.portfolio,
            risk_limits=self.risk_limits,
            broker=self.broker_simulator,
            logger=self.logger,
        )
        return run_backtest(bars=bars, strategy=self.strategy, context=context)

    def preflight_live(self) -> str:
        if self.mode != AppMode.LIVE:
            raise RuntimeError(f"Unsupported mode '{self.mode}'.")

        self._single_symbol(mode_name="live")
        return "Live mode preflight passed (no orders were submitted)."

    def run_live_paper(self) -> BacktestResult:
        if self.mode != AppMode.LIVE:
            raise RuntimeError(f"Unsupported mode '{self.mode}'.")

        symbol = self._single_symbol(mode_name="live")
        bars = self.data_provider.load_bars(symbol)
        context = BacktestContext(
            portfolio=self.portfolio,
            risk_limits=self.risk_limits,
            broker=self.broker_simulator,
            logger=self.logger,
        )
        return run_backtest(bars=bars, strategy=self.strategy, context=context)

    def _single_symbol(self, mode_name: str) -> str:
        if len(self.symbols) != 1:
            raise RuntimeError(
                f"Current scaffold supports exactly one symbol for {mode_name} mode."
            )
        return self.symbols[0]


def build_services(settings: AppSettings) -> AppServices:
    ensure_logging()
    logger = StructuredLogger("trading_system", log_format=StructuredLogFormat.JSON)

    if settings.mode == AppMode.LIVE:
        _require_live_api_key()

    return AppServices(
        mode=settings.mode,
        strategy=MomentumStrategy(trade_quantity=settings.backtest.trade_quantity),
        data_provider=_build_data_provider(settings),
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


def _require_live_api_key() -> None:
    provider = EnvSecretProvider()
    provider.get_secret("TRADING_SYSTEM_API_KEY")


def _build_data_provider(settings: AppSettings) -> MarketDataProvider:
    if settings.provider == "mock":
        bars_by_symbol = {symbol: build_sample_bars(symbol=symbol) for symbol in settings.symbols}
        return InMemoryMarketDataProvider(bars_by_symbol=bars_by_symbol)

    csv_dir = Path(os.getenv("TRADING_SYSTEM_CSV_DIR", "data/market"))
    csv_by_symbol: dict[str, Path] = {}
    missing_symbols: list[str] = []
    for symbol in settings.symbols:
        csv_path = csv_dir / f"{symbol}.csv"
        if not csv_path.exists():
            missing_symbols.append(symbol)
            continue
        csv_by_symbol[symbol] = csv_path

    if missing_symbols:
        missing = ", ".join(missing_symbols)
        raise RuntimeError(
            "CSV provider requires symbol files under "
            f"'{csv_dir}' (missing: {missing})."
        )

    return CsvMarketDataProvider(csv_by_symbol=csv_by_symbol)
