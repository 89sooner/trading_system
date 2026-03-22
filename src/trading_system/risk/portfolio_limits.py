"""Portfolio-level risk guards: daily drawdown limit and per-position SL/TP.

These guards operate *above* the symbol-level ``RiskLimits`` and protect the
entire account from runaway losses across a trading session.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

ZERO = Decimal("0")


@dataclass(slots=True)
class PortfolioRiskLimits:
    """Portfolio-wide risk parameters evaluated each trading step.

    Parameters
    ----------
    max_daily_drawdown_pct:
        Fraction of *session_peak_equity* that, once breached, blocks all new
        entries for the rest of the session.  E.g. ``Decimal("0.05")`` = 5 %.
    session_peak_equity:
        The highest equity value seen in the current session.  Set to starting
        equity at boot; updated by ``update_peak`` on each step.
    sl_pct:
        Optional per-position stop-loss expressed as a fraction of average
        entry cost.  E.g. ``Decimal("0.02")`` exits longs when price drops 2 %.
    tp_pct:
        Optional per-position take-profit expressed as a fraction of average
        entry cost.  E.g. ``Decimal("0.05")`` exits longs when price rises 5 %.
    """

    max_daily_drawdown_pct: Decimal
    session_peak_equity: Decimal
    sl_pct: Decimal | None = None
    tp_pct: Decimal | None = None

    # ------------------------------------------------------------------
    # Drawdown guard
    # ------------------------------------------------------------------

    def update_peak(self, current_equity: Decimal) -> None:
        """Advance the session high-water mark when equity improves."""
        if current_equity > self.session_peak_equity:
            self.session_peak_equity = current_equity

    def is_daily_limit_breached(self, current_equity: Decimal) -> bool:
        """Return ``True`` when equity has fallen below the allowed drawdown."""
        if self.session_peak_equity == ZERO:
            return False
        drawdown = (self.session_peak_equity - current_equity) / self.session_peak_equity
        return drawdown >= self.max_daily_drawdown_pct

    # ------------------------------------------------------------------
    # Per-position SL / TP checks  (long positions only for Phase 3)
    # ------------------------------------------------------------------

    def sl_triggered(
        self,
        avg_cost: Decimal,
        mark: Decimal,
        quantity: Decimal,
    ) -> bool:
        """Return ``True`` when a long position has fallen to its stop-loss."""
        if self.sl_pct is None or avg_cost == ZERO or quantity <= ZERO:
            return False
        threshold = avg_cost * (1 - self.sl_pct)
        return mark <= threshold

    def tp_triggered(
        self,
        avg_cost: Decimal,
        mark: Decimal,
        quantity: Decimal,
    ) -> bool:
        """Return ``True`` when a long position has risen to its take-profit."""
        if self.tp_pct is None or avg_cost == ZERO or quantity <= ZERO:
            return False
        threshold = avg_cost * (1 + self.tp_pct)
        return mark >= threshold
