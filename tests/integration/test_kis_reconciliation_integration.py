"""Integration tests for KIS reconciliation flow."""

from decimal import Decimal
from unittest.mock import MagicMock

from trading_system.app.loop import LiveTradingLoop
from trading_system.core.ops import StructuredLogFormat, StructuredLogger
from trading_system.execution.broker import AccountBalanceSnapshot
from trading_system.execution.reconciliation import reconcile
from trading_system.portfolio.book import PortfolioBook


def test_reconciliation_detects_cash_and_position_drift() -> None:
    """When broker snapshot differs from local book, reconciliation adjusts both."""
    book = PortfolioBook(
        cash=Decimal("1000000"),
        positions={"005930": Decimal("5")},
        average_costs={"005930": Decimal("70000")},
    )
    snapshot = AccountBalanceSnapshot(
        cash=Decimal("950000"),
        positions={"005930": Decimal("7")},
        average_costs={"005930": Decimal("70200")},
    )
    logger = StructuredLogger("integration.recon.drift", log_format=StructuredLogFormat.JSON)

    result = reconcile(book=book, snapshot=snapshot, logger=logger)

    assert result.adjusted_cash is True
    assert "005930" in result.adjusted_symbols
    assert book.cash == Decimal("950000")
    assert book.positions["005930"] == Decimal("7")
    assert book.average_costs["005930"] == Decimal("70200")


def test_reconciliation_skips_pending_symbol_and_freezes_cash() -> None:
    """Symbols with pending orders are not adjusted; cash is frozen."""
    book = PortfolioBook(
        cash=Decimal("1000000"),
        positions={"005930": Decimal("5")},
        average_costs={"005930": Decimal("70000")},
    )
    snapshot = AccountBalanceSnapshot(
        cash=Decimal("900000"),
        positions={"005930": Decimal("8")},
        average_costs={"005930": Decimal("70100")},
        pending_symbols=("005930",),
    )
    logger = StructuredLogger("integration.recon.pending", log_format=StructuredLogFormat.JSON)

    result = reconcile(book=book, snapshot=snapshot, logger=logger)

    assert result.frozen_cash is True
    assert result.adjusted_symbols == ()
    assert book.cash == Decimal("1000000")
    assert book.positions["005930"] == Decimal("5")
    assert book.average_costs["005930"] == Decimal("70000")


def test_reconciliation_removes_liquidated_position() -> None:
    """When broker shows zero holdings, local position and avg cost are removed."""
    book = PortfolioBook(
        cash=Decimal("500000"),
        positions={"005930": Decimal("3")},
        average_costs={"005930": Decimal("70000")},
    )
    snapshot = AccountBalanceSnapshot(
        cash=Decimal("710000"),
        positions={},
    )
    logger = StructuredLogger("integration.recon.liquidated", log_format=StructuredLogFormat.JSON)

    result = reconcile(book=book, snapshot=snapshot, logger=logger)

    assert result.adjusted_cash is True
    assert "005930" in result.adjusted_symbols
    assert book.cash == Decimal("710000")
    assert "005930" not in book.positions
    assert "005930" not in book.average_costs


def test_live_reconciliation_skips_fail_closed_when_open_order_query_fails() -> None:
    services = MagicMock()
    services.logger = MagicMock()
    services.portfolio = PortfolioBook(
        cash=Decimal("1000000"),
        positions={"005930": Decimal("5")},
    )
    services.broker_simulator.get_open_orders.side_effect = RuntimeError("open orders failed")

    loop = LiveTradingLoop(services=services)

    loop._maybe_reconcile()

    services.broker_simulator.get_account_balance.assert_not_called()
    assert services.portfolio.cash == Decimal("1000000")
    assert services.portfolio.positions["005930"] == Decimal("5")
