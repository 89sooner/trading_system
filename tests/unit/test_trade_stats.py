from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from trading_system.analytics.trade_stats import summarize_trades
from trading_system.analytics.trades import CompletedTrade, extract_trades

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fill(symbol: str, side: str, qty: str, price: str, ts: str) -> dict:
    return {
        "event": "order.filled",
        "payload": {
            "symbol": symbol,
            "side": side,
            "filled_quantity": qty,
            "fill_price": price,
            "timestamp": ts,
        },
    }


# ---------------------------------------------------------------------------
# Original tests
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Edge-case tests — partial fills
# ---------------------------------------------------------------------------


def test_partial_fill_single_buy_split_across_two_sells() -> None:
    """Buy 10, sell 4, sell 6 → two completed trades from one lot."""
    events = [
        _fill("X", "buy", "10", "100", "2024-01-01T00:00:00+00:00"),
        _fill("X", "sell", "4", "110", "2024-01-01T00:01:00+00:00"),
        _fill("X", "sell", "6", "105", "2024-01-01T00:02:00+00:00"),
    ]
    trades = extract_trades(events)

    assert len(trades) == 2
    assert trades[0].quantity == Decimal("4")
    assert trades[0].pnl == Decimal("40")  # (110-100)*4
    assert trades[1].quantity == Decimal("6")
    assert trades[1].pnl == Decimal("30")  # (105-100)*6


def test_partial_fill_sell_spans_multiple_buy_lots() -> None:
    """Buy 3, buy 5 → sell 6 matches across two lots (FIFO)."""
    events = [
        _fill("X", "buy", "3", "100", "2024-01-01T00:00:00+00:00"),
        _fill("X", "buy", "5", "110", "2024-01-01T00:01:00+00:00"),
        _fill("X", "sell", "6", "120", "2024-01-01T00:02:00+00:00"),
    ]
    trades = extract_trades(events)

    assert len(trades) == 2
    # First lot: 3 @ 100, exit 120 → pnl = 60
    assert trades[0].quantity == Decimal("3")
    assert trades[0].pnl == Decimal("60")
    # Second lot partial: 3 @ 110, exit 120 → pnl = 30
    assert trades[1].quantity == Decimal("3")
    assert trades[1].pnl == Decimal("30")


# ---------------------------------------------------------------------------
# Edge-case tests — scale-in
# ---------------------------------------------------------------------------


def test_scale_in_multiple_buys_single_sell() -> None:
    """Scale into a position with 3 buys, then close with a single sell."""
    events = [
        _fill("X", "buy", "2", "100", "2024-01-01T00:00:00+00:00"),
        _fill("X", "buy", "3", "105", "2024-01-01T00:01:00+00:00"),
        _fill("X", "buy", "5", "110", "2024-01-01T00:02:00+00:00"),
        _fill("X", "sell", "10", "120", "2024-01-01T00:03:00+00:00"),
    ]
    trades = extract_trades(events)

    assert len(trades) == 3
    total_pnl = sum(t.pnl for t in trades)
    # (120-100)*2 + (120-105)*3 + (120-110)*5 = 40+45+50 = 135
    assert total_pnl == Decimal("135")


# ---------------------------------------------------------------------------
# Edge-case tests — scale-out
# ---------------------------------------------------------------------------


def test_scale_out_single_buy_multiple_sells() -> None:
    """Enter full position, exit in three tranches."""
    events = [
        _fill("X", "buy", "10", "100", "2024-01-01T00:00:00+00:00"),
        _fill("X", "sell", "3", "110", "2024-01-01T00:01:00+00:00"),
        _fill("X", "sell", "4", "115", "2024-01-01T00:02:00+00:00"),
        _fill("X", "sell", "3", "105", "2024-01-01T00:03:00+00:00"),
    ]
    trades = extract_trades(events)

    assert len(trades) == 3
    total_pnl = sum(t.pnl for t in trades)
    # (110-100)*3 + (115-100)*4 + (105-100)*3 = 30+60+15 = 105
    assert total_pnl == Decimal("105")


# ---------------------------------------------------------------------------
# Edge-case tests — flat-then-reopen
# ---------------------------------------------------------------------------


def test_flat_then_reopen_creates_separate_trades() -> None:
    """Close position to flat, then re-enter. Must produce separate trades."""
    events = [
        _fill("X", "buy", "5", "100", "2024-01-01T00:00:00+00:00"),
        _fill("X", "sell", "5", "110", "2024-01-01T00:01:00+00:00"),
        # Position is flat
        _fill("X", "buy", "3", "200", "2024-01-01T00:10:00+00:00"),
        _fill("X", "sell", "3", "190", "2024-01-01T00:11:00+00:00"),
    ]
    trades = extract_trades(events)

    assert len(trades) == 2
    assert trades[0].pnl == Decimal("50")  # (110-100)*5
    assert trades[1].pnl == Decimal("-30")  # (190-200)*3


# ---------------------------------------------------------------------------
# Edge-case tests — empty trades
# ---------------------------------------------------------------------------


def test_extract_trades_empty_events() -> None:
    assert extract_trades([]) == []


def test_extract_trades_only_buys_no_sells() -> None:
    events = [
        _fill("X", "buy", "5", "100", "2024-01-01T00:00:00+00:00"),
    ]
    trades = extract_trades(events)
    assert trades == []


def test_extract_trades_sell_without_prior_buy() -> None:
    """Sell with no open lots should produce no trades."""
    events = [
        _fill("X", "sell", "5", "100", "2024-01-01T00:00:00+00:00"),
    ]
    trades = extract_trades(events)
    assert trades == []


def test_extract_trades_ignores_non_fill_events() -> None:
    events = [
        _fill("X", "buy", "1", "100", "2024-01-01T00:00:00+00:00"),
    ]
    # Override event type to non-fill
    events[0]["event"] = "order.created"
    trades = extract_trades(events)
    assert trades == []


def test_summarize_trades_empty_list() -> None:
    stats = summarize_trades([])
    assert stats.trade_count == 0
    assert stats.win_rate == Decimal("0")
    assert stats.risk_reward_ratio == Decimal("0")
    assert stats.max_drawdown == Decimal("0")
    assert stats.average_time_in_market_seconds == 0.0


def test_summarize_trades_all_winners() -> None:
    trades = [
        CompletedTrade(
            symbol="X",
            entry_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            exit_time=datetime(2024, 1, 1, 0, 5, tzinfo=timezone.utc),
            entry_price=Decimal("100"),
            exit_price=Decimal("110"),
            quantity=Decimal("1"),
            pnl=Decimal("10"),
        ),
    ]
    stats = summarize_trades(trades)
    assert stats.win_rate == Decimal("1")
    assert stats.risk_reward_ratio == Decimal("0")  # no losses → 0
