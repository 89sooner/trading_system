from dataclasses import dataclass


@dataclass(slots=True)
class RiskSettings:
    max_position: float
    max_notional: float
    max_order_size: float


@dataclass(slots=True)
class BacktestSettings:
    starting_cash: float
    fee_bps: float
