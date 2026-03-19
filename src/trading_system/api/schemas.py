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


class StrategyConfigDTO(BaseModel):
    type: Literal["pattern_signal"] = "pattern_signal"
    profile_id: str | None = None
    pattern_set_id: str | None = None
    label_to_side: dict[str, Literal["buy", "sell", "hold"]] = Field(default_factory=dict)
    trade_quantity: Decimal | None = None
    threshold_overrides: dict[str, float] = Field(default_factory=dict)


class BacktestRunRequestDTO(BaseModel):
    mode: Literal["backtest"] = "backtest"
    symbols: list[str] = Field(min_length=1)
    provider: Literal["mock", "csv", "kis"] = "mock"
    broker: Literal["paper", "kis"] = "paper"
    live_execution: Literal["preflight", "paper", "live"] = "preflight"
    risk: RiskSettingsDTO
    backtest: BacktestSettingsDTO
    strategy: StrategyConfigDTO | None = None


class LivePreflightRequestDTO(BaseModel):
    mode: Literal["live"] = "live"
    symbols: list[str] = Field(min_length=1)
    provider: Literal["mock", "csv", "kis"] = "mock"
    broker: Literal["paper", "kis"] = "paper"
    live_execution: Literal["preflight", "paper", "live"] = "preflight"
    risk: RiskSettingsDTO
    backtest: BacktestSettingsDTO
    strategy: StrategyConfigDTO | None = None


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
    signals: list[EventDTO]
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


class PatternBarDTO(BaseModel):
    timestamp: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


class PatternTrainingExampleDTO(BaseModel):
    label: str = Field(min_length=1)
    bars: list[PatternBarDTO] = Field(min_length=2)


class PatternTrainRequestDTO(BaseModel):
    name: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    default_threshold: float = Field(ge=0, le=1)
    examples: list[PatternTrainingExampleDTO] = Field(min_length=1)


class LearnedPatternDTO(BaseModel):
    label: str
    lookback: int
    sample_size: int
    threshold: float
    prototype: list[float]


class PatternSetDTO(BaseModel):
    pattern_set_id: str
    name: str
    symbol: str
    default_threshold: float
    examples_count: int
    patterns: list[LearnedPatternDTO]


class PatternSetSaveRequestDTO(BaseModel):
    pattern_set_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    default_threshold: float = Field(ge=0, le=1)
    examples_count: int = Field(ge=1)
    patterns: list[LearnedPatternDTO] = Field(min_length=1)


class StrategyProfileCreateDTO(BaseModel):
    strategy_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    strategy: StrategyConfigDTO


class StrategyProfileDTO(BaseModel):
    strategy_id: str
    name: str
    strategy: StrategyConfigDTO
