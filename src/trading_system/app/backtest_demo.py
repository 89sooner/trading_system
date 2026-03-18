from dataclasses import dataclass
from decimal import Decimal

from trading_system.app.sample_data import build_sample_bars as _build_sample_bars
from trading_system.app.services import build_services
from trading_system.app.settings import (
    AppMode,
    AppSettings,
    BacktestSettings,
    LiveExecutionMode,
    RiskSettings,
)
from trading_system.backtest.engine import BacktestResult
from trading_system.core.types import MarketBar


@dataclass(slots=True)
class SmokeBacktestConfig:
    symbol: str = "BTCUSDT"
    starting_cash: Decimal = Decimal("10000")
    fee_bps: Decimal = Decimal("5")
    trade_quantity: Decimal = Decimal("0.1")
    max_position: Decimal = Decimal("1.0")
    max_notional: Decimal = Decimal("100000")
    max_order_size: Decimal = Decimal("0.25")


def build_sample_bars(symbol: str = "BTCUSDT") -> list[MarketBar]:
    return _build_sample_bars(symbol=symbol)


def run_smoke_backtest(config: SmokeBacktestConfig | None = None) -> BacktestResult:
    if config is None:
        config = SmokeBacktestConfig()

    settings = AppSettings(
        mode=AppMode.BACKTEST,
        symbols=(config.symbol,),
        provider="mock",
        broker="paper",
        live_execution=LiveExecutionMode.PREFLIGHT,
        risk=RiskSettings(
            max_position=config.max_position,
            max_notional=config.max_notional,
            max_order_size=config.max_order_size,
        ),
        backtest=BacktestSettings(
            starting_cash=config.starting_cash,
            fee_bps=config.fee_bps,
            trade_quantity=config.trade_quantity,
        ),
    )
    services = build_services(settings)
    return services.run()


def format_result(result: BacktestResult) -> str:
    final_portfolio = result.final_portfolio
    position_items = ", ".join(
        f"{symbol}={quantity}" for symbol, quantity in sorted(final_portfolio.positions.items())
    ) or "flat"
    equity_curve = ", ".join(str(value) for value in result.equity_curve)

    return "\n".join(
        [
            "Smoke backtest result",
            f"processed_bars: {result.processed_bars}",
            f"executed_trades: {result.executed_trades}",
            f"rejected_signals: {result.rejected_signals}",
            f"cash: {final_portfolio.cash}",
            f"positions: {position_items}",
            f"total_return: {result.total_return}",
            f"equity_curve: [{equity_curve}]",
        ]
    )
