import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

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
    KisQuoteMarketDataProvider,
    MarketDataProvider,
)
from trading_system.execution.broker import (
    BpsCommissionPolicy,
    BpsSlippagePolicy,
    BrokerSimulator,
    FixedRatioFillPolicy,
    PolicyBrokerSimulator,
    ResilientBroker,
)
from trading_system.execution.kis_adapter import KisBrokerAdapter
from trading_system.portfolio.book import PortfolioBook
from trading_system.risk.limits import RiskLimits
from trading_system.strategy.base import Strategy
from trading_system.strategy.example import MomentumStrategy
from trading_system.integrations.kis import KisApiClient


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
    live_preflight_check: Callable[[str], str] | None = None

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

        symbol = self._single_symbol(mode_name="live")
        if self.live_preflight_check is not None:
            return self.live_preflight_check(symbol)
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
    kis_client = _build_kis_client_if_needed(settings)

    if settings.mode == AppMode.LIVE:
        _require_live_credentials(settings)

    return AppServices(
        mode=settings.mode,
        strategy=MomentumStrategy(trade_quantity=settings.backtest.trade_quantity),
        data_provider=_build_data_provider(settings, kis_client=kis_client),
        risk_limits=RiskLimits(
            max_position=settings.risk.max_position,
            max_notional=settings.risk.max_notional,
            max_order_size=settings.risk.max_order_size,
        ),
        broker_simulator=ResilientBroker(
            delegate=_build_broker(settings, kis_client=kis_client),
        ),
        portfolio=PortfolioBook(cash=settings.backtest.starting_cash),
        symbols=settings.symbols,
        logger=logger,
        live_preflight_check=_build_live_preflight(settings, kis_client=kis_client),
    )


def _require_live_credentials(settings: AppSettings) -> None:
    if settings.provider == "kis" or settings.broker == "kis":
        KisApiClient.from_env()
        return

    provider = EnvSecretProvider()
    provider.get_secret("TRADING_SYSTEM_API_KEY")


def _build_data_provider(
    settings: AppSettings,
    *,
    kis_client: KisApiClient | None,
) -> MarketDataProvider:
    if settings.provider == "mock":
        bars_by_symbol = {symbol: build_sample_bars(symbol=symbol) for symbol in settings.symbols}
        return InMemoryMarketDataProvider(bars_by_symbol=bars_by_symbol)
    if settings.provider == "kis":
        if kis_client is None:
            raise RuntimeError("KIS provider requires KIS API credentials.")
        return KisQuoteMarketDataProvider(client=kis_client)

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
def _build_broker(
    settings: AppSettings,
    *,
    kis_client: KisApiClient | None,
) -> BrokerSimulator:
    if settings.broker == "kis":
        if kis_client is None:
            raise RuntimeError("KIS broker requires KIS API credentials.")
        return KisBrokerAdapter(client=kis_client)

    return PolicyBrokerSimulator(
        fill_quantity_policy=FixedRatioFillPolicy(),
        slippage_policy=BpsSlippagePolicy(),
        commission_policy=BpsCommissionPolicy(bps=settings.backtest.fee_bps),
    )


def _build_kis_client_if_needed(settings: AppSettings) -> KisApiClient | None:
    if settings.provider != "kis" and settings.broker != "kis":
        return None
    return KisApiClient.from_env()


def _build_live_preflight(
    settings: AppSettings,
    *,
    kis_client: KisApiClient | None,
) -> Callable[[str], str] | None:
    if settings.mode != AppMode.LIVE or kis_client is None:
        return None

    def preflight(symbol: str) -> str:
        quote = kis_client.preflight_symbol(symbol)
        return (
            "KIS live preflight passed "
            f"(symbol={quote.symbol}, price={quote.price}, volume={quote.volume}). "
            "No orders were submitted."
        )

    return preflight
