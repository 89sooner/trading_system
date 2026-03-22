import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from trading_system.portfolio.book import PortfolioBook


class PortfolioRepository(Protocol):
    def save(self, book: PortfolioBook) -> None:
        """Save the portfolio book state."""

    def load(self) -> PortfolioBook | None:
        """Load the portfolio book state. Returns None if not found."""


class FilePortfolioRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, book: PortfolioBook) -> None:
        raw_dict = asdict(book)
        
        # Convert Decimals to strings for JSON serialization
        serializable_dict = {
            "cash": str(raw_dict["cash"]),
            "positions": {k: str(v) for k, v in raw_dict.get("positions", {}).items()},
            "average_costs": {k: str(v) for k, v in raw_dict.get("average_costs", {}).items()},
            "realized_pnl": {k: str(v) for k, v in raw_dict.get("realized_pnl", {}).items()},
            "fees_paid": {k: str(v) for k, v in raw_dict.get("fees_paid", {}).items()},
            "keep_flat_positions": raw_dict.get("keep_flat_positions", False),
        }
        
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(serializable_dict, f, indent=2)
        temp_path.replace(self.path)

    def load(self) -> PortfolioBook | None:
        if not self.path.exists():
            return None
            
        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            
        return PortfolioBook(
            cash=Decimal(data["cash"]),
            positions={k: Decimal(v) for k, v in data.get("positions", {}).items()},
            average_costs={k: Decimal(v) for k, v in data.get("average_costs", {}).items()},
            realized_pnl={k: Decimal(v) for k, v in data.get("realized_pnl", {}).items()},
            fees_paid={k: Decimal(v) for k, v in data.get("fees_paid", {}).items()},
            keep_flat_positions=data.get("keep_flat_positions", False),
        )
