import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from trading_system.app.equity_writer import EquityWriterProtocol, FileEquityWriter
from trading_system.app.loop import LiveTradingLoop
from trading_system.app.sample_data import build_sample_bars
from trading_system.app.settings import AppMode, AppSettings, LiveExecutionMode
from trading_system.app.state import AppRunnerState, LiveRuntimeState
from trading_system.backtest.engine import BacktestContext, BacktestResult, run_backtest
from trading_system.core.compat import UTC
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
from trading_system.execution.order_audit import OrderAuditRepository
from trading_system.integrations.kis import KisApiClient, is_krx_market_open
from trading_system.notifications.webhook import WebhookNotifier, build_webhook_notifier
from trading_system.patterns.repository import PatternSetRepository
from trading_system.portfolio.book import PortfolioBook
from trading_system.portfolio.repository import (
    FilePortfolioRepository,
    PortfolioRepository,
)
from trading_system.risk.limits import RiskLimits
from trading_system.risk.portfolio_limits import PortfolioRiskLimits
from trading_system.strategy.base import Strategy
from trading_system.strategy.factory import build_strategies
from trading_system.strategy.repository import StrategyProfileRepository


@dataclass(slots=True)
class ReadinessCheck:
    name: str
    status: str
    summary: str
    details: dict[str, str] | None = None


@dataclass(slots=True)
class SymbolReadiness:
    symbol: str
    status: str
    summary: str
    price: str | None = None
    volume: str | None = None


@dataclass(slots=True)
class PreflightCheckResult:
    ready: bool
    reasons: list[str]
    quote_summary: dict[str, str] | None
    quote_summaries: list[dict[str, str]] | None
    symbol_count: int
    message: str
    blocking_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks: list[ReadinessCheck] = field(default_factory=list)
    symbol_checks: list[SymbolReadiness] = field(default_factory=list)
    next_allowed_actions: list[str] = field(default_factory=list)
    checked_at: str | None = None


@dataclass(slots=True)
class AppServices:
    mode: AppMode
    provider: str
    broker: str
    live_execution: LiveExecutionMode
    strategy: Strategy
    data_provider: MarketDataProvider
    risk_limits: RiskLimits
    broker_simulator: ResilientBroker
    portfolio: PortfolioBook
    symbols: tuple[str, ...]
    logger: StructuredLogger
    live_preflight_check: Callable[[tuple[str, ...]], PreflightCheckResult] | None = None
    portfolio_repository: PortfolioRepository | None = None
    strategies: dict[str, Strategy] | None = None
    portfolio_risk: PortfolioRiskLimits | None = None
    webhook_notifier: WebhookNotifier | None = None
    order_audit_repository: OrderAuditRepository | None = None

    def run(self, audit_owner_id: str | None = None) -> BacktestResult:
        if self.mode != AppMode.BACKTEST:
            raise RuntimeError(f"Unsupported mode '{self.mode}'.")

        bars = self._merged_bars()
        context = BacktestContext(
            portfolio=self.portfolio,
            risk_limits=self.risk_limits,
            broker=self.broker_simulator,
            logger=self.logger,
            portfolio_risk=self.portfolio_risk,
            runtime_state=LiveRuntimeState(state=AppRunnerState.RUNNING),
            marks={},
            order_audit_repository=self.order_audit_repository,
            order_audit_scope="backtest",
            order_audit_owner_id=audit_owner_id,
        )
        return run_backtest(
            bars=bars,
            strategy=self.strategy,
            context=context,
            strategy_by_symbol=self.strategies,
        )

    def preflight_live(self) -> PreflightCheckResult:
        if self.mode != AppMode.LIVE:
            raise RuntimeError(f"Unsupported mode '{self.mode}'.")

        if self.live_preflight_check is not None:
            return self.live_preflight_check(self.symbols)

        return PreflightCheckResult(
            ready=True,
            reasons=[],
            quote_summary=None,
            quote_summaries=None,
            symbol_count=len(self.symbols),
            message="Live mode preflight passed (no orders were submitted).",
            blocking_reasons=[],
            warnings=[],
            checks=[
                ReadinessCheck(
                    name="runtime_path",
                    status="pass",
                    summary="Generic live runtime path is available for paper execution.",
                ),
                ReadinessCheck(
                    name="order_submission",
                    status="warn",
                    summary="Real order submission is only supported on the KIS live path.",
                ),
            ],
            symbol_checks=[
                SymbolReadiness(
                    symbol=symbol,
                    status="pass",
                    summary="No provider-specific preflight was required for this symbol.",
                )
                for symbol in self.symbols
            ],
            next_allowed_actions=["paper"],
            checked_at=datetime.now(UTC).isoformat(),
        )

    def run_live_paper(self) -> None:
        if self.mode != AppMode.LIVE:
            raise RuntimeError(f"Unsupported mode '{self.mode}'.")

        self.build_live_loop().run()

    def build_live_loop(self, session_id: str | None = None) -> LiveTradingLoop:
        if self.mode != AppMode.LIVE:
            raise RuntimeError(f"Unsupported mode '{self.mode}'.")

        resolved_session_id = session_id or datetime.now(UTC).strftime("live_%Y%m%d_%H%M%S")
        equity_writer = _create_equity_writer(resolved_session_id)
        return LiveTradingLoop(
            services=self,
            equity_writer=equity_writer,
            audit_owner_id=resolved_session_id,
        )

    def run_live_execution(self) -> None:
        if self.mode != AppMode.LIVE:
            raise RuntimeError(f"Unsupported mode '{self.mode}'.")
        self.validate_live_execution_guards()
        self.build_live_loop().run()

    def validate_live_execution_guards(self) -> None:
        if self.mode != AppMode.LIVE:
            raise RuntimeError(f"Unsupported mode '{self.mode}'.")
        if self.live_execution != LiveExecutionMode.LIVE:
            raise RuntimeError("Live order validation requires --live-execution live.")
        if self.provider != "kis" or self.broker != "kis":
            raise RuntimeError("Live order submission requires '--provider kis --broker kis'.")
        if not _is_live_orders_enabled():
            raise RuntimeError(
                "Live order submission is disabled. "
                "Set TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true to enable."
            )
        if not is_krx_market_open():
            raise RuntimeError(
                "Live order submission is blocked outside KRX market hours "
                "(weekdays 09:00-15:30 KST)."
            )

    def strategy_for(self, symbol: str) -> Strategy:
        if self.strategies is None:
            return self.strategy
        return self.strategies[symbol]

    def _merged_bars(self):
        symbol_order = {symbol: idx for idx, symbol in enumerate(self.symbols)}
        merged = [bar for symbol in self.symbols for bar in self.data_provider.load_bars(symbol)]
        return sorted(merged, key=lambda bar: (bar.timestamp, symbol_order[bar.symbol]))


def build_services(
    settings: AppSettings,
    *,
    order_audit_repository: OrderAuditRepository | None = None,
) -> AppServices:
    ensure_logging()
    logger = StructuredLogger("trading_system", log_format=StructuredLogFormat.JSON)
    kis_client = _build_kis_client_if_needed(settings)
    pattern_repository = PatternSetRepository(_resolve_pattern_dir())
    strategy_repository = StrategyProfileRepository(_resolve_strategy_dir())
    portfolio_repository = FilePortfolioRepository(_resolve_portfolio_path())

    if settings.mode == AppMode.LIVE:
        _require_live_credentials(settings)

    saved_book = portfolio_repository.load()
    if saved_book is not None and settings.mode == AppMode.LIVE:
        portfolio = saved_book
        logger.emit(
            "portfolio.loaded",
            severity=20,
            payload={
                "path": str(_resolve_portfolio_path()),
                "cash": str(portfolio.cash),
            },
        )
    else:
        portfolio = PortfolioBook(cash=settings.backtest.starting_cash)
        logger.emit("portfolio.initialized", severity=20, payload={"cash": str(portfolio.cash)})

    strategies = build_strategies(
        settings,
        symbols=settings.symbols,
        pattern_repository=pattern_repository,
        strategy_repository=strategy_repository,
    )
    primary_strategy = strategies[settings.symbols[0]]

    webhook_notifier = build_webhook_notifier()
    if webhook_notifier is not None:
        logger.subscribe(webhook_notifier.as_subscriber())

    return AppServices(
        mode=settings.mode,
        provider=settings.provider,
        broker=settings.broker,
        live_execution=settings.live_execution,
        strategy=primary_strategy,
        strategies=strategies,
        data_provider=_build_data_provider(settings, kis_client=kis_client),
        risk_limits=RiskLimits(
            max_position=settings.risk.max_position,
            max_notional=settings.risk.max_notional,
            max_order_size=settings.risk.max_order_size,
        ),
        portfolio_risk=_build_portfolio_risk(settings, portfolio),
        broker_simulator=ResilientBroker(
            delegate=_build_broker(settings, kis_client=kis_client),
        ),
        portfolio=portfolio,
        symbols=settings.symbols,
        logger=logger,
        live_preflight_check=_build_live_preflight(settings, kis_client=kis_client),
        portfolio_repository=(portfolio_repository if settings.mode == AppMode.LIVE else None),
        webhook_notifier=webhook_notifier,
        order_audit_repository=order_audit_repository,
    )


def _build_portfolio_risk(
    settings: AppSettings,
    portfolio: PortfolioBook,
) -> PortfolioRiskLimits | None:
    if settings.portfolio_risk is None:
        return None
    return PortfolioRiskLimits(
        max_daily_drawdown_pct=settings.portfolio_risk.max_daily_drawdown_pct,
        session_peak_equity=portfolio.total_equity({}),
        sl_pct=settings.portfolio_risk.sl_pct,
        tp_pct=settings.portfolio_risk.tp_pct,
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
        return KisQuoteMarketDataProvider(
            client=kis_client,
            bars_per_load=_resolve_kis_live_sample_size(settings),
        )

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
            f"CSV provider requires symbol files under '{csv_dir}' (missing: {missing})."
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
) -> Callable[[tuple[str, ...]], PreflightCheckResult] | None:
    if settings.mode != AppMode.LIVE or kis_client is None:
        return None

    def preflight(symbols: tuple[str, ...]) -> PreflightCheckResult:
        checked_at = datetime.now(UTC).isoformat()
        reasons: list[str] = []
        blocking_reasons: list[str] = []
        warnings: list[str] = []
        ready = True
        quote_summaries: list[dict[str, str]] = []
        primary_quote_summary: dict[str, str] | None = None
        checks: list[ReadinessCheck] = [
            ReadinessCheck(
                name="broker_route",
                status=(
                    "pass"
                    if settings.provider == "kis" and settings.broker == "kis"
                    else "warn"
                ),
                summary=(
                    "KIS provider and broker route are selected."
                    if settings.provider == "kis" and settings.broker == "kis"
                    else (
                        "Paper execution is available, but real orders require "
                        "provider=kis and broker=kis."
                    )
                ),
            )
        ]
        symbol_checks: list[SymbolReadiness] = []

        market_open = is_krx_market_open()
        if not market_open:
            reasons.append("market_closed")
            if settings.live_execution == LiveExecutionMode.LIVE:
                blocking_reasons.append("market_closed")
                ready = False
            else:
                warnings.append("market_closed")
        checks.append(
            ReadinessCheck(
                name="market_session",
                status=(
                    "pass"
                    if market_open
                    else "fail" if settings.live_execution == LiveExecutionMode.LIVE else "warn"
                ),
                summary=(
                    "KRX regular session is currently open."
                    if market_open
                    else (
                        "KRX regular session is closed. "
                        "Live orders are blocked outside market hours."
                    )
                ),
            )
        )

        live_order_gate_status = "pass"
        live_order_gate_summary = "Paper execution is available from the dashboard."
        if settings.provider == "kis" and settings.broker == "kis":
            if _is_live_orders_enabled():
                live_order_gate_summary = (
                    "Live-order environment flag is enabled for the guarded KIS route."
                )
            else:
                live_order_gate_status = "warn"
                live_order_gate_summary = (
                    "Live-order environment flag is disabled. Paper execution is still allowed."
                )
                if settings.live_execution == LiveExecutionMode.LIVE:
                    ready = False
                    reasons.append("live_orders_disabled")
                    blocking_reasons.append("live_orders_disabled")
        checks.append(
            ReadinessCheck(
                name="live_order_gate",
                status=live_order_gate_status,
                summary=live_order_gate_summary,
                details={"live_execution": settings.live_execution.value},
            )
        )

        for symbol in symbols:
            try:
                quote = kis_client.preflight_symbol(symbol)
                quote_summary = {
                    "symbol": quote.symbol,
                    "price": str(quote.price),
                    "volume": str(quote.volume),
                }
                if primary_quote_summary is None and quote.symbol == symbols[0]:
                    primary_quote_summary = quote_summary
                quote_summaries.append(quote_summary)
                if quote.volume == 0:
                    reasons.append(f"zero_volume:{symbol}")
                    warnings.append(f"zero_volume:{symbol}")
                    symbol_checks.append(
                        SymbolReadiness(
                            symbol=symbol,
                            status="warn",
                            summary="Quote was returned but the sampled volume was zero.",
                            price=quote_summary["price"],
                            volume=quote_summary["volume"],
                        )
                    )
                    continue
                symbol_checks.append(
                    SymbolReadiness(
                        symbol=symbol,
                        status="pass",
                        summary="Quote and sampled volume look valid.",
                        price=quote_summary["price"],
                        volume=quote_summary["volume"],
                    )
                )
            except Exception as exc:
                reason = f"quote_error:{symbol}: {exc}"
                reasons.append(reason)
                blocking_reasons.append(reason)
                ready = False
                symbol_checks.append(
                    SymbolReadiness(
                        symbol=symbol,
                        status="fail",
                        summary=str(exc),
                    )
                )

        checks.append(
            ReadinessCheck(
                name="symbol_quotes",
                status=(
                    "fail"
                    if any(item.status == "fail" for item in symbol_checks)
                    else "warn"
                    if any(item.status == "warn" for item in symbol_checks)
                    else "pass"
                ),
                summary=(
                    "At least one symbol quote failed validation."
                    if any(item.status == "fail" for item in symbol_checks)
                    else "At least one symbol reported zero sampled volume."
                    if any(item.status == "warn" for item in symbol_checks)
                    else "All symbols returned valid quote samples."
                ),
                details={"symbol_count": str(len(symbols))},
            )
        )

        if ready and not reasons:
            sym = symbols[0] if symbols else "N/A"
            price = primary_quote_summary["price"] if primary_quote_summary else "N/A"
            volume = primary_quote_summary["volume"] if primary_quote_summary else "N/A"
            message = (
                f"KIS live preflight passed "
                f"(symbols={len(symbols)}, primary_symbol={sym}, "
                f"primary_price={price}, primary_volume={volume}). "
                f"No orders were submitted."
            )
        else:
            message = f"KIS live preflight completed with issues: {', '.join(reasons)}"

        next_allowed_actions: list[str] = []
        if not blocking_reasons:
            next_allowed_actions.append("paper")
            if (
                settings.provider == "kis"
                and settings.broker == "kis"
                and market_open
                and _is_live_orders_enabled()
                and not any(item.status == "fail" for item in symbol_checks)
            ):
                next_allowed_actions.append("live")
        next_allowed_actions.append("review")

        return PreflightCheckResult(
            ready=ready,
            reasons=reasons,
            quote_summary=primary_quote_summary,
            quote_summaries=quote_summaries or None,
            symbol_count=len(symbols),
            message=message,
            blocking_reasons=blocking_reasons,
            warnings=warnings,
            checks=checks,
            symbol_checks=symbol_checks,
            next_allowed_actions=next_allowed_actions,
            checked_at=checked_at,
        )

    return preflight


def _is_live_orders_enabled() -> bool:
    return os.getenv("TRADING_SYSTEM_ENABLE_LIVE_ORDERS", "").strip().lower() == "true"


def _resolve_kis_live_sample_size(settings: AppSettings) -> int:
    if settings.mode != AppMode.LIVE or settings.live_execution != LiveExecutionMode.LIVE:
        return 1

    configured = os.getenv("TRADING_SYSTEM_LIVE_BAR_SAMPLES", "2").strip()
    try:
        return max(int(configured), 2)
    except ValueError as exc:
        raise RuntimeError(
            "TRADING_SYSTEM_LIVE_BAR_SAMPLES must be an integer value greater than or equal to 2."
        ) from exc


def _resolve_pattern_dir() -> Path:
    return Path(os.getenv("TRADING_SYSTEM_PATTERN_DIR", "configs/patterns"))


def _resolve_strategy_dir() -> Path:
    return Path(os.getenv("TRADING_SYSTEM_STRATEGY_DIR", "configs/strategies"))


def _resolve_portfolio_path() -> Path:
    return Path(os.getenv("TRADING_SYSTEM_PORTFOLIO_DIR", "data/portfolio")) / "book.json"


def _create_equity_writer(session_id: str) -> EquityWriterProtocol | None:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        from trading_system.app.supabase_equity_writer import SupabaseEquityWriter
        return SupabaseEquityWriter(database_url, session_id)
    equity_dir = Path(os.getenv("TRADING_SYSTEM_EQUITY_DIR", "data/equity"))
    return FileEquityWriter(equity_dir, session_id)
