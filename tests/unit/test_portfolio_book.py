from decimal import Decimal

from trading_system.portfolio.book import PortfolioBook


def test_apply_fill_tracks_average_cost_realized_unrealized_and_fees() -> None:
    book = PortfolioBook(cash=Decimal("1000"))

    book.apply_fill("BTCUSDT", Decimal("2"), Decimal("100"), fee=Decimal("1"))
    book.apply_fill("BTCUSDT", Decimal("1"), Decimal("130"), fee=Decimal("0.5"))
    book.apply_fill("BTCUSDT", Decimal("-1.5"), Decimal("140"), fee=Decimal("0.25"))

    assert book.positions["BTCUSDT"] == Decimal("1.5")
    assert book.average_costs["BTCUSDT"] == Decimal("110")
    assert book.realized_pnl["BTCUSDT"] == Decimal("45")
    assert book.unrealized_pnl({"BTCUSDT": Decimal("150")}) == {"BTCUSDT": Decimal("60")}
    assert book.fees_paid["BTCUSDT"] == Decimal("1.75")
    assert book.total_fees_paid() == Decimal("1.75")


def test_apply_fill_removes_flat_position_by_default() -> None:
    book = PortfolioBook(cash=Decimal("1000"))

    book.apply_fill("BTCUSDT", Decimal("1"), Decimal("100"))
    book.apply_fill("BTCUSDT", Decimal("-1"), Decimal("110"))

    assert "BTCUSDT" not in book.positions
    assert "BTCUSDT" not in book.average_costs
    assert book.realized_pnl["BTCUSDT"] == Decimal("10")


def test_apply_fill_keeps_flat_position_when_enabled() -> None:
    book = PortfolioBook(cash=Decimal("1000"), keep_flat_positions=True)

    book.apply_fill("BTCUSDT", Decimal("1"), Decimal("100"))
    book.apply_fill("BTCUSDT", Decimal("-1"), Decimal("110"))

    assert book.positions["BTCUSDT"] == Decimal("0")
    assert book.average_costs["BTCUSDT"] == Decimal("0")
    assert book.realized_pnl["BTCUSDT"] == Decimal("10")
