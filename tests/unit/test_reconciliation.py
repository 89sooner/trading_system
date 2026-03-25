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
