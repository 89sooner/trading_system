from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from trading_system.analytics.trade_stats import summarize_trades
from trading_system.analytics.trades import CompletedTrade, extract_trades


def test_extract_trades_pairs_buys_and_sells_fifo() -> None:
    events = [
        {
            "event": "order.filled",
            "payload": {
                "symbol": "BTCUSDT",
                "side": "buy",
                "filled_quantity": "1",
                "fill_price": "100",
                "timestamp": "2024-01-01T00:00:00+00:00",
            },
        },
        {
            "event": "order.filled",
            "payload": {
                "symbol": "BTCUSDT",
                "side": "sell",
                "filled_quantity": "1",
                "fill_price": "110",
                "timestamp": "2024-01-01T00:05:00+00:00",
            },
        },
    ]

    trades = extract_trades(events)

    assert len(trades) == 1
    assert trades[0].pnl == Decimal("10")
    assert trades[0].holding_seconds == 300.0


def test_summarize_trades_returns_required_metrics() -> None:
    trades = [
        CompletedTrade(
            symbol="BTCUSDT",
            entry_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            exit_time=datetime(2024, 1, 1, 0, 5, tzinfo=timezone.utc),
            entry_price=Decimal("100"),
            exit_price=Decimal("110"),
            quantity=Decimal("1"),
            pnl=Decimal("10"),
        ),
        CompletedTrade(
            symbol="ETHUSDT",
            entry_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            exit_time=datetime(2024, 1, 1, 0, 10, tzinfo=timezone.utc),
            entry_price=Decimal("50"),
            exit_price=Decimal("45"),
            quantity=Decimal("1"),
            pnl=Decimal("-5"),
        ),
    ]

    stats = summarize_trades(trades)

    assert stats.trade_count == 2
    assert stats.win_rate == Decimal("0.5")
    assert stats.risk_reward_ratio == Decimal("2")
    assert stats.max_drawdown < Decimal("0")
    assert stats.average_time_in_market_seconds == 450.0
