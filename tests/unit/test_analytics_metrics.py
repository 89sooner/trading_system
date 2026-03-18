from datetime import UTC, datetime
from decimal import Decimal

from trading_system.analytics.metrics import (
    cumulative_return,
    drawdown_series,
    max_drawdown,
    performance_metrics,
    volatility,
    win_rate,
)
from trading_system.analytics.view_models import EventViewModel, build_backtest_analytics_view_model


def test_metrics_for_standard_equity_curve() -> None:
    curve = [Decimal("100"), Decimal("110"), Decimal("90"), Decimal("120")]

    assert cumulative_return(curve) == Decimal("0.2")
    assert drawdown_series(curve) == [
        Decimal("0"),
        Decimal("0"),
        Decimal("-0.1818181818181818181818181818"),
        Decimal("0"),
    ]
    assert max_drawdown(curve) == Decimal("-0.1818181818181818181818181818")
    assert volatility(curve) == Decimal("0.2106199883968629028036863276")
    assert win_rate(curve) == Decimal("0.6666666666666666666666666667")

    metrics = performance_metrics(curve)
    assert metrics.cumulative_return == Decimal("0.2")
    assert metrics.max_drawdown == Decimal("-0.1818181818181818181818181818")
    assert metrics.volatility == Decimal("0.2106199883968629028036863276")
    assert metrics.win_rate == Decimal("0.6666666666666666666666666667")


def test_metrics_handle_empty_curve_and_single_point() -> None:
    assert cumulative_return([]) == Decimal("0")
    assert cumulative_return([Decimal("10")]) == Decimal("0")
    assert drawdown_series([]) == []
    assert max_drawdown([]) == Decimal("0")
    assert volatility([]) == Decimal("0")
    assert win_rate([]) == Decimal("0")


def test_metrics_handle_zero_or_negative_starting_equity_deterministically() -> None:
    zero_start_curve = [Decimal("0"), Decimal("10"), Decimal("5")]
    negative_curve = [Decimal("-100"), Decimal("-90"), Decimal("-110")]

    assert cumulative_return(zero_start_curve) == Decimal("0")
    assert volatility(zero_start_curve) == Decimal("0.25")
    assert win_rate(zero_start_curve) == Decimal("0")

    assert cumulative_return(negative_curve) == Decimal("0.1")
    assert drawdown_series(negative_curve) == [
        Decimal("0"),
        Decimal("0"),
        Decimal("-0.2222222222222222222222222222"),
    ]
    assert max_drawdown(negative_curve) == Decimal("-0.2222222222222222222222222222")
    assert volatility(negative_curve) == Decimal("0.1611111111111111111111111111")
    assert win_rate(negative_curve) == Decimal("0.5")


def test_view_model_includes_metrics_and_drawdown_curves_for_api_schema() -> None:
    timestamps = [
        datetime(2024, 1, 1, tzinfo=UTC),
        datetime(2024, 1, 2, tzinfo=UTC),
        datetime(2024, 1, 3, tzinfo=UTC),
    ]
    equity_curve = [Decimal("100"), Decimal("120"), Decimal("90")]

    view_model = build_backtest_analytics_view_model(
        timestamps=timestamps,
        equity_curve=equity_curve,
        orders=[
            EventViewModel(
                event="order.created",
                payload={"symbol": "BTCUSDT", "quantity": Decimal("1")},
            )
        ],
        risk_rejections=[
            EventViewModel(
                event="risk.rejected",
                payload={"symbol": "BTCUSDT", "requested_quantity": Decimal("2")},
            )
        ],
    )

    assert view_model.summary.return_value == Decimal("-0.1")
    assert view_model.summary.max_drawdown == Decimal("-0.25")
    assert view_model.summary.volatility == Decimal("0.225")
    assert view_model.summary.win_rate == Decimal("0.5")
    assert view_model.equity_curve[0].timestamp == "2024-01-01T00:00:00Z"
    assert [point.drawdown for point in view_model.drawdown_curve] == [
        Decimal("0"),
        Decimal("0"),
        Decimal("-0.25"),
    ]
    assert [event.event for event in view_model.orders] == ["order.created"]
    assert [event.event for event in view_model.risk_rejections] == ["risk.rejected"]
