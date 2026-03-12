from dataclasses import dataclass
from decimal import Decimal

from trading_system.portfolio.book import PortfolioBook
from trading_system.risk.limits import RiskLimits


@dataclass(slots=True)
class BacktestContext:
    portfolio: PortfolioBook
    risk_limits: RiskLimits
    fee_bps: Decimal
