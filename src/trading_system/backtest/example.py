from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from trading_system.backtest.engine import BacktestContext, BacktestResult, run_backtest
from trading_system.core.types import MarketBar
from trading_system.portfolio.book import PortfolioBook
from trading_system.risk.limits import RiskLimits
from trading_system.strategy.example import MomentumStrategy


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
    closes = [
        Decimal("100"),
        Decimal("101"),
        Decimal("103"),
        Decimal("102"),
        Decimal("104"),
        Decimal("105"),
        Decimal("103"),
    ]
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)

    return [
        MarketBar(
            symbol=symbol,
            timestamp=start + timedelta(minutes=index),
            open=close,
            high=close,
            low=close,
            close=close,
            volume=Decimal("1"),
        )
        for index, close in enumerate(closes)
    ]


def run_smoke_backtest(config: SmokeBacktestConfig | None = None) -> BacktestResult:
    if config is None:
        config = SmokeBacktestConfig()

    context = BacktestContext(
        portfolio=PortfolioBook(cash=config.starting_cash),
        risk_limits=RiskLimits(
            max_position=config.max_position,
            max_notional=config.max_notional,
            max_order_size=config.max_order_size,
        ),
        fee_bps=config.fee_bps,
    )
    strategy = MomentumStrategy(trade_quantity=config.trade_quantity)
    bars = build_sample_bars(symbol=config.symbol)
    return run_backtest(bars=bars, strategy=strategy, context=context)


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


def main() -> None:
    print(format_result(run_smoke_backtest()))


if __name__ == "__main__":
    main()
