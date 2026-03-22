from decimal import Decimal
from pathlib import Path

from trading_system.portfolio.book import PortfolioBook
from trading_system.portfolio.repository import FilePortfolioRepository


def test_file_portfolio_repository_roundtrip(tmp_path: Path):
    repo_path = tmp_path / "test_book.json"
    repository = FilePortfolioRepository(repo_path)
    
    # 1. Ensure load returns None when file doesn't exist
    assert repository.load() is None
    
    # 2. Create and save a book
    original_book = PortfolioBook(
        cash=Decimal("15000.50"),
        positions={"BTCUSDT": Decimal("0.5"), "ETHUSDT": Decimal("-10.0")},
        average_costs={"BTCUSDT": Decimal("40000"), "ETHUSDT": Decimal("2000")},
        realized_pnl={"BTCUSDT": Decimal("500"), "ETHUSDT": Decimal("-100")},
        fees_paid={"BTCUSDT": Decimal("10"), "ETHUSDT": Decimal("5")},
        keep_flat_positions=True
    )
    
    repository.save(original_book)
    assert repo_path.exists()
    
    # 3. Load the book and verify contents
    loaded_book = repository.load()
    assert loaded_book is not None
    assert loaded_book.cash == Decimal("15000.50")
    assert loaded_book.positions["BTCUSDT"] == Decimal("0.5")
    assert loaded_book.positions["ETHUSDT"] == Decimal("-10.0")
    assert loaded_book.average_costs["BTCUSDT"] == Decimal("40000")
    assert loaded_book.realized_pnl["ETHUSDT"] == Decimal("-100")
    assert loaded_book.fees_paid["BTCUSDT"] == Decimal("10")
    assert loaded_book.keep_flat_positions is True
