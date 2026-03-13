from decimal import Decimal

from trading_system.analytics.metrics import (
    cumulative_return,
    drawdown_series,
    max_drawdown,
    performance_metrics,
    volatility,
    win_rate,
)


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
