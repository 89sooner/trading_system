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
    provider: Literal["mock", "csv", "kis"] = "mock"
    broker: Literal["paper", "kis"] = "paper"
    live_execution: Literal["preflight", "paper"] = "preflight"
    risk: RiskSettingsDTO
    backtest: BacktestSettingsDTO


class LivePreflightRequestDTO(BaseModel):
    mode: Literal["live"] = "live"
    symbols: list[str] = Field(min_length=1)
    provider: Literal["mock", "csv", "kis"] = "mock"
    broker: Literal["paper", "kis"] = "paper"
    live_execution: Literal["preflight", "paper"] = "preflight"
    risk: RiskSettingsDTO
    backtest: BacktestSettingsDTO


class BacktestResultDTO(BaseModel):
    class SummaryDTO(BaseModel):
        return_value: str = Field(alias="return")
        max_drawdown: str
        volatility: str
        win_rate: str

        model_config = ConfigDict(populate_by_name=True)

    class EquityPointDTO(BaseModel):
        timestamp: str
        equity: str

    class DrawdownPointDTO(BaseModel):
        timestamp: str
        drawdown: str

    class EventDTO(BaseModel):
        event: str
        payload: dict[str, str]

    summary: SummaryDTO
    equity_curve: list[EquityPointDTO]
    drawdown_curve: list[DrawdownPointDTO]
    orders: list[EventDTO]
    risk_rejections: list[EventDTO]


class BacktestRunAcceptedDTO(BaseModel):
    run_id: str
    status: Literal["succeeded", "failed"]


class BacktestRunStatusDTO(BaseModel):
    run_id: str
    status: Literal["running", "succeeded", "failed"]
    started_at: str
    finished_at: str
    input_symbols: list[str]
    mode: Literal["backtest", "live"]
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
