from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from trading_system.analytics.trades import CompletedTrade

ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class TradeStats:
    trade_count: int
    win_rate: Decimal
    risk_reward_ratio: Decimal
    max_drawdown: Decimal
    average_time_in_market_seconds: float


def summarize_trades(trades: Sequence[CompletedTrade]) -> TradeStats:
    if not trades:
        return TradeStats(
            trade_count=0,
            win_rate=ZERO,
            risk_reward_ratio=ZERO,
            max_drawdown=ZERO,
            average_time_in_market_seconds=0.0,
        )

    wins = [trade.pnl for trade in trades if trade.pnl > ZERO]
    losses = [abs(trade.pnl) for trade in trades if trade.pnl < ZERO]
    win_rate = Decimal(len(wins)) / Decimal(len(trades))
    average_win = sum(wins, start=ZERO) / Decimal(len(wins)) if wins else ZERO
    average_loss = sum(losses, start=ZERO) / Decimal(len(losses)) if losses else ZERO
    risk_reward_ratio = average_win / average_loss if average_loss > ZERO else ZERO

    cumulative = ZERO
    peak = ZERO
    max_dd = ZERO
    for trade in trades:
        cumulative += trade.pnl
        if cumulative > peak:
            peak = cumulative
        if peak == ZERO:
            continue
        drawdown = (cumulative - peak) / abs(peak)
        if drawdown < max_dd:
            max_dd = drawdown

    avg_holding = sum(trade.holding_seconds for trade in trades) / len(trades)

    return TradeStats(
        trade_count=len(trades),
        win_rate=win_rate,
        risk_reward_ratio=risk_reward_ratio,
        max_drawdown=max_dd,
        average_time_in_market_seconds=avg_holding,
    )
