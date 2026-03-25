from __future__ import annotations

from dataclasses import dataclass

from trading_system.core.ops import StructuredLogger
from trading_system.execution.broker import AccountBalanceSnapshot
from trading_system.portfolio.book import ZERO, PortfolioBook


@dataclass(slots=True, frozen=True)
class ReconciliationResult:
    adjusted_cash: bool
    adjusted_symbols: tuple[str, ...]
    frozen_cash: bool


def reconcile(
    *,
    book: PortfolioBook,
    snapshot: AccountBalanceSnapshot,
    logger: StructuredLogger,
) -> ReconciliationResult:
    pending = set(snapshot.pending_symbols)
    adjusted_symbols: list[str] = []
    frozen_cash = bool(pending)

    if not frozen_cash and book.cash != snapshot.cash:
        logger.emit(
            "portfolio.reconciliation.cash_adjusted",
            severity=30,
            payload={"from": str(book.cash), "to": str(snapshot.cash)},
        )
        book.cash = snapshot.cash

    if frozen_cash:
        logger.emit(
            "portfolio.reconciliation.cash_frozen",
            severity=30,
            payload={"pending_symbols": sorted(pending)},
        )

    all_symbols = set(book.positions) | set(snapshot.positions)
    for symbol in sorted(all_symbols):
        if symbol in pending:
            logger.emit(
                "portfolio.reconciliation.symbol_skipped",
                severity=30,
                payload={"symbol": symbol, "reason": "in_transit"},
            )
            continue

        target_qty = snapshot.positions.get(symbol, ZERO)
        current_qty = book.positions.get(symbol, ZERO)
        if current_qty == target_qty:
            continue

        adjusted_symbols.append(symbol)
        logger.emit(
            "portfolio.reconciliation.position_adjusted",
            severity=30,
            payload={"symbol": symbol, "from": str(current_qty), "to": str(target_qty)},
        )
        if target_qty == ZERO:
            book.positions.pop(symbol, None)
            book.average_costs.pop(symbol, None)
        else:
            book.positions[symbol] = target_qty
            book.average_costs[symbol] = book.average_costs.get(symbol, ZERO)

    return ReconciliationResult(
        adjusted_cash=not frozen_cash,
        adjusted_symbols=tuple(adjusted_symbols),
        frozen_cash=frozen_cash,
    )
