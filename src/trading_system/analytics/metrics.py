from collections.abc import Sequence
from decimal import Decimal


def cumulative_return(equity_curve: Sequence[Decimal]) -> Decimal:
    if len(equity_curve) < 2:
        return Decimal("0")

    starting_equity = equity_curve[0]
    ending_equity = equity_curve[-1]
    if starting_equity == 0:
        return Decimal("0")

    return (ending_equity - starting_equity) / starting_equity
