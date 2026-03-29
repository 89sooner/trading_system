from decimal import Decimal

from trading_system.core.ops import StructuredLogFormat, StructuredLogger
from trading_system.execution.broker import AccountBalanceSnapshot
from trading_system.execution.reconciliation import reconcile
from trading_system.portfolio.book import PortfolioBook


def test_reconciliation_adjusts_positions_and_cash_without_pending_orders() -> None:
    book = PortfolioBook(
        cash=Decimal("100"),
        positions={"BTCUSDT": Decimal("1")},
        average_costs={"BTCUSDT": Decimal("100")},
    )
    snapshot = AccountBalanceSnapshot(
        cash=Decimal("120"),
        positions={"BTCUSDT": Decimal("2")},
    )
    logger = StructuredLogger("test.recon", log_format=StructuredLogFormat.JSON)

    result = reconcile(book=book, snapshot=snapshot, logger=logger)

    assert result.adjusted_cash is True
    assert result.adjusted_symbols == ("BTCUSDT",)
    assert book.cash == Decimal("120")
    assert book.positions["BTCUSDT"] == Decimal("2")


def test_reconciliation_syncs_average_costs_from_snapshot() -> None:
    book = PortfolioBook(
        cash=Decimal("100"),
        positions={"BTCUSDT": Decimal("1")},
        average_costs={"BTCUSDT": Decimal("90")},
    )
    snapshot = AccountBalanceSnapshot(
        cash=Decimal("120"),
        positions={"BTCUSDT": Decimal("2")},
        average_costs={"BTCUSDT": Decimal("105")},
    )
    logger = StructuredLogger("test.recon.avgcost", log_format=StructuredLogFormat.JSON)

    reconcile(book=book, snapshot=snapshot, logger=logger)

    assert book.average_costs["BTCUSDT"] == Decimal("105")


def test_reconciliation_syncs_average_cost_when_quantity_unchanged() -> None:
    """Average cost drift is corrected even when position quantity matches."""
    book = PortfolioBook(
        cash=Decimal("100"),
        positions={"BTCUSDT": Decimal("5")},
        average_costs={"BTCUSDT": Decimal("90")},
    )
    snapshot = AccountBalanceSnapshot(
        cash=Decimal("100"),
        positions={"BTCUSDT": Decimal("5")},
        average_costs={"BTCUSDT": Decimal("95")},
    )
    logger = StructuredLogger("test.recon.avgcost.same_qty", log_format=StructuredLogFormat.JSON)

    result = reconcile(book=book, snapshot=snapshot, logger=logger)

    assert book.average_costs["BTCUSDT"] == Decimal("95")
    assert book.positions["BTCUSDT"] == Decimal("5")
    assert result.adjusted_cash is True  # no pending symbols, so cash adjustment was attempted


def test_reconciliation_skips_symbol_and_freezes_cash_when_pending_order_exists() -> None:
    book = PortfolioBook(
        cash=Decimal("100"),
        positions={"BTCUSDT": Decimal("1")},
        average_costs={"BTCUSDT": Decimal("100")},
    )
    snapshot = AccountBalanceSnapshot(
        cash=Decimal("120"),
        positions={"BTCUSDT": Decimal("2")},
        pending_symbols=("BTCUSDT",),
    )
    logger = StructuredLogger("test.recon.pending", log_format=StructuredLogFormat.JSON)

    result = reconcile(book=book, snapshot=snapshot, logger=logger)

    assert result.frozen_cash is True
    assert result.adjusted_symbols == ()
    assert book.cash == Decimal("100")
    assert book.positions["BTCUSDT"] == Decimal("1")
