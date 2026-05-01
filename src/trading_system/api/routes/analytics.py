from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, HTTPException, status

from trading_system.analytics.trade_stats import summarize_trades
from trading_system.analytics.trades import extract_trades
from trading_system.api.routes import backtest as backtest_routes
from trading_system.api.schemas import TradeAnalyticsResponseDTO, TradeDTO, TradeStatsDTO

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/backtests/{run_id}/trades", response_model=TradeAnalyticsResponseDTO)
async def get_backtest_trade_analytics(run_id: str) -> TradeAnalyticsResponseDTO:
    run = backtest_routes._RUN_REPOSITORY.get(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backtest run not found")
    if run.status in {"queued", "running"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Backtest run is still {run.status}.",
        )
    if run.status in {"failed", "cancelled"}:
        detail = run.error or "Backtest run failed."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    if run.result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backtest run not found")

    trades = extract_trades(run.result.orders)
    stats = summarize_trades(trades)
    return TradeAnalyticsResponseDTO(
        stats=TradeStatsDTO(
            trade_count=stats.trade_count,
            win_rate=_to_string(stats.win_rate),
            risk_reward_ratio=_to_string(stats.risk_reward_ratio),
            max_drawdown=_to_string(stats.max_drawdown),
            average_time_in_market_seconds=stats.average_time_in_market_seconds,
        ),
        trades=[
            TradeDTO(
                symbol=trade.symbol,
                entry_time=trade.entry_time.isoformat(),
                exit_time=trade.exit_time.isoformat(),
                entry_price=_to_string(trade.entry_price),
                exit_price=_to_string(trade.exit_price),
                quantity=_to_string(trade.quantity),
                pnl=_to_string(trade.pnl),
                holding_seconds=trade.holding_seconds,
            )
            for trade in trades
        ],
    )


def _to_string(value: Decimal) -> str:
    return format(value, "f")
