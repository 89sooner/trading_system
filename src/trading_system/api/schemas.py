from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RiskSettingsDTO(BaseModel):
    max_position: Decimal
    max_notional: Decimal
    max_order_size: Decimal


class BacktestSettingsDTO(BaseModel):
    starting_cash: Decimal
    fee_bps: Decimal
    trade_quantity: Decimal


class BacktestRunRequestDTO(BaseModel):
    mode: Literal["backtest"] = "backtest"
    symbols: list[str] = Field(min_length=1)
    provider: Literal["mock", "csv"] = "mock"
    broker: Literal["paper"] = "paper"
    live_execution: Literal["preflight", "paper"] = "preflight"
    risk: RiskSettingsDTO
    backtest: BacktestSettingsDTO


class LivePreflightRequestDTO(BaseModel):
    mode: Literal["live"] = "live"
    symbols: list[str] = Field(min_length=1)
    provider: Literal["mock", "csv"] = "mock"
    broker: Literal["paper"] = "paper"
    live_execution: Literal["preflight", "paper"] = "preflight"
    risk: RiskSettingsDTO
    backtest: BacktestSettingsDTO


class BacktestResultDTO(BaseModel):
    processed_bars: int
    executed_trades: int
    rejected_signals: int
    cash: Decimal
    positions: dict[str, Decimal]
    total_return: Decimal
    equity_curve: list[Decimal]


class BacktestRunAcceptedDTO(BaseModel):
    run_id: str
    status: Literal["succeeded", "failed"]


class BacktestRunStatusDTO(BaseModel):
    run_id: str
    status: Literal["running", "succeeded", "failed"]
    result: BacktestResultDTO | None = None
    error: str | None = None


class LivePreflightResponseDTO(BaseModel):
    status: Literal["ok"] = "ok"
    message: str
    paper_result: BacktestResultDTO | None = None


class ErrorResponseDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_code: str
    message: str
