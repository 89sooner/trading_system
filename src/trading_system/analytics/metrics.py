from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal


ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class PerformanceMetrics:
    cumulative_return: Decimal
    max_drawdown: Decimal
    volatility: Decimal
    win_rate: Decimal


def cumulative_return(equity_curve: Sequence[Decimal]) -> Decimal:
    if len(equity_curve) < 2:
        return ZERO

    starting_equity = equity_curve[0]
    ending_equity = equity_curve[-1]
    if starting_equity == ZERO:
        return ZERO

    return (ending_equity - starting_equity) / starting_equity


def drawdown_series(equity_curve: Sequence[Decimal]) -> list[Decimal]:
    if not equity_curve:
        return []

    peak = equity_curve[0]
    drawdowns: list[Decimal] = []
    for equity in equity_curve:
        if equity > peak:
            peak = equity
        if peak == ZERO:
            drawdowns.append(ZERO)
            continue
        drawdowns.append((equity - peak) / abs(peak))
    return drawdowns


def max_drawdown(equity_curve: Sequence[Decimal]) -> Decimal:
    drawdowns = drawdown_series(equity_curve)
    if not drawdowns:
        return ZERO
    return min(drawdowns)


def volatility(equity_curve: Sequence[Decimal]) -> Decimal:
    period_returns = _period_returns(equity_curve)
    if not period_returns:
        return ZERO

    count = Decimal(len(period_returns))
    mean_return = sum(period_returns, start=ZERO) / count
    variance = sum(((value - mean_return) ** 2 for value in period_returns), start=ZERO) / count
    return variance.sqrt()


def win_rate(equity_curve: Sequence[Decimal]) -> Decimal:
    period_returns = _period_returns(equity_curve)
    if not period_returns:
        return ZERO

    wins = sum(Decimal("1") for value in period_returns if value > ZERO)
    return wins / Decimal(len(period_returns))


def performance_metrics(equity_curve: Sequence[Decimal]) -> PerformanceMetrics:
    return PerformanceMetrics(
        cumulative_return=cumulative_return(equity_curve),
        max_drawdown=max_drawdown(equity_curve),
        volatility=volatility(equity_curve),
        win_rate=win_rate(equity_curve),
    )


def _period_returns(equity_curve: Sequence[Decimal]) -> list[Decimal]:
    if len(equity_curve) < 2:
        return []

    returns: list[Decimal] = []
    for previous, current in zip(equity_curve, equity_curve[1:]):
        if previous == ZERO:
            returns.append(ZERO)
            continue
        returns.append((current - previous) / abs(previous))
    return returns
