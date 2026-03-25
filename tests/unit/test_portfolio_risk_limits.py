"""Unit tests for PortfolioRiskLimits and step-level integration."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

from trading_system.app.state import AppRunnerState, LiveRuntimeState
from trading_system.core.types import MarketBar
from trading_system.execution.step import TradingContext, execute_trading_step
from trading_system.portfolio.book import PortfolioBook
from trading_system.risk.limits import RiskLimits
from trading_system.risk.portfolio_limits import PortfolioRiskLimits

ZERO = Decimal("0")


# ---------------------------------------------------------------------------
# PortfolioRiskLimits unit tests
# ---------------------------------------------------------------------------


class TestDrawdownLimit:
    def _limits(self, peak: str, max_dd: str = "0.05") -> PortfolioRiskLimits:
        return PortfolioRiskLimits(
            max_daily_drawdown_pct=Decimal(max_dd),
            session_peak_equity=Decimal(peak),
        )

    def test_no_breach_above_threshold(self) -> None:
        limits = self._limits("10000")
        assert not limits.is_daily_limit_breached(Decimal("9600"))  # 4 % < 5 %

    def test_breach_at_threshold(self) -> None:
        limits = self._limits("10000")
        assert limits.is_daily_limit_breached(Decimal("9500"))  # exactly 5 %

    def test_breach_below_threshold(self) -> None:
        limits = self._limits("10000")
        assert limits.is_daily_limit_breached(Decimal("9000"))  # 10 % > 5 %

    def test_peak_update_advances(self) -> None:
        limits = self._limits("10000")
        limits.update_peak(Decimal("11000"))
        assert limits.session_peak_equity == Decimal("11000")

    def test_peak_update_does_not_retreat(self) -> None:
        limits = self._limits("10000")
        limits.update_peak(Decimal("9000"))
        assert limits.session_peak_equity == Decimal("10000")

    def test_zero_peak_never_breaches(self) -> None:
        limits = PortfolioRiskLimits(
            max_daily_drawdown_pct=Decimal("0.05"),
            session_peak_equity=ZERO,
        )
        assert not limits.is_daily_limit_breached(ZERO)


class TestStopLoss:
    def _limits(self, sl_pct: str = "0.02") -> PortfolioRiskLimits:
        return PortfolioRiskLimits(
            max_daily_drawdown_pct=Decimal("0.10"),
            session_peak_equity=Decimal("10000"),
            sl_pct=Decimal(sl_pct),
        )

    def test_not_triggered_above_threshold(self) -> None:
        limits = self._limits()
        # avg_cost=100, mark=99 == 1 % drop; sl=2 % → not triggered
        assert not limits.sl_triggered(Decimal("100"), Decimal("99"), Decimal("1"))

    def test_triggered_at_threshold(self) -> None:
        limits = self._limits()
        # mark = 100 * (1 - 0.02) = 98
        assert limits.sl_triggered(Decimal("100"), Decimal("98"), Decimal("1"))

    def test_triggered_below_threshold(self) -> None:
        limits = self._limits()
        assert limits.sl_triggered(Decimal("100"), Decimal("95"), Decimal("1"))

    def test_no_sl_config_never_triggers(self) -> None:
        limits = PortfolioRiskLimits(
            max_daily_drawdown_pct=Decimal("0.05"),
            session_peak_equity=Decimal("10000"),
            sl_pct=None,
        )
        assert not limits.sl_triggered(Decimal("100"), Decimal("80"), Decimal("1"))

    def test_zero_or_short_qty_never_triggers(self) -> None:
        limits = self._limits()
        # Short position (negative qty) should not trigger long stop
        assert not limits.sl_triggered(Decimal("100"), Decimal("80"), Decimal("-1"))
        assert not limits.sl_triggered(Decimal("100"), Decimal("80"), ZERO)


class TestTakeProfit:
    def _limits(self, tp_pct: str = "0.05") -> PortfolioRiskLimits:
        return PortfolioRiskLimits(
            max_daily_drawdown_pct=Decimal("0.10"),
            session_peak_equity=Decimal("10000"),
            tp_pct=Decimal(tp_pct),
        )

    def test_not_triggered_below_threshold(self) -> None:
        # mark=104 < 100*(1+0.05)=105 → not triggered
        assert not self._limits().tp_triggered(Decimal("100"), Decimal("104"), Decimal("1"))

    def test_triggered_at_threshold(self) -> None:
        assert self._limits().tp_triggered(Decimal("100"), Decimal("105"), Decimal("1"))

    def test_triggered_above_threshold(self) -> None:
        assert self._limits().tp_triggered(Decimal("100"), Decimal("120"), Decimal("1"))


# ---------------------------------------------------------------------------
# Regression: step skips trading when daily limit is breached
# ---------------------------------------------------------------------------


def _make_bar(close: str = "100") -> MarketBar:
    return MarketBar(
        symbol="BTCUSDT",
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        open=Decimal(close),
        high=Decimal(close),
        low=Decimal(close),
        close=Decimal(close),
        volume=Decimal("1"),
    )


def _make_context(
    cash: str = "100",
    portfolio_risk: PortfolioRiskLimits | None = None,
) -> TradingContext:
    portfolio = PortfolioBook(cash=Decimal(cash))
    risk = RiskLimits(
        max_position=Decimal("10"),
        max_notional=Decimal("100000"),
        max_order_size=Decimal("1"),
    )
    broker = MagicMock()
    return TradingContext(
        portfolio=portfolio,
        risk_limits=risk,
        broker=broker,
        portfolio_risk=portfolio_risk,
        runtime_state=LiveRuntimeState(state=AppRunnerState.RUNNING),
        marks={},
    )


class TestDrawdownRegressionInStep:
    """verify that execute_trading_step early-exits when daily limit is breached."""

    def test_step_skips_strategy_when_limit_breached(self) -> None:
        # Set peak high so that current cash (100) breaches the 5% drawdown
        pr = PortfolioRiskLimits(
            max_daily_drawdown_pct=Decimal("0.05"),
            session_peak_equity=Decimal("1000"),  # current_equity=100 → 90% drop
        )
        context = _make_context(cash="100", portfolio_risk=pr)
        strategy = MagicMock()
        strategy.evaluate = MagicMock()

        bar = _make_bar("100")
        events = execute_trading_step(bar=bar, strategy=strategy, context=context)

        # Strategy should never be called when limit is breached
        strategy.evaluate.assert_not_called()
        assert events.signal is None
        assert events.order_created is None

    def test_step_runs_normally_when_limit_not_breached(self) -> None:
        pr = PortfolioRiskLimits(
            max_daily_drawdown_pct=Decimal("0.05"),
            session_peak_equity=Decimal("100"),  # current_equity ≈ peak → no breach
        )
        context = _make_context(cash="100", portfolio_risk=pr)

        from trading_system.strategy.base import SignalSide, StrategySignal

        strategy = MagicMock()
        strategy.evaluate.return_value = StrategySignal(
            side=SignalSide.HOLD, quantity=ZERO, reason="test_hold"
        )

        bar = _make_bar("100")
        execute_trading_step(bar=bar, strategy=strategy, context=context)

        # Strategy MUST be called when equity is healthy
        strategy.evaluate.assert_called_once_with(bar)

    def test_drawdown_breach_moves_runtime_to_emergency(self) -> None:
        pr = PortfolioRiskLimits(
            max_daily_drawdown_pct=Decimal("0.05"),
            session_peak_equity=Decimal("1000"),
        )
        context = _make_context(cash="100", portfolio_risk=pr)
        strategy = MagicMock()
        bar = _make_bar("100")

        execute_trading_step(bar=bar, strategy=strategy, context=context)

        assert context.runtime_state is not None
        assert context.runtime_state.state == AppRunnerState.EMERGENCY
