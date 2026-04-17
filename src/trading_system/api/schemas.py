from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RiskSettingsDTO(BaseModel):
    max_position: Decimal
    max_notional: Decimal
    max_order_size: Decimal


class PortfolioRiskSettingsDTO(BaseModel):
    max_daily_drawdown_pct: Decimal
    sl_pct: Decimal | None = None
    tp_pct: Decimal | None = None


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
    portfolio_risk: PortfolioRiskSettingsDTO | None = None
    backtest: BacktestSettingsDTO
    strategy: StrategyConfigDTO | None = None


class LivePreflightRequestDTO(BaseModel):
    mode: Literal["live"] = "live"
    symbols: list[str] = Field(min_length=1)
    provider: Literal["mock", "csv", "kis"] = "mock"
    broker: Literal["paper", "kis"] = "paper"
    live_execution: Literal["preflight", "paper", "live"] = "preflight"
    risk: RiskSettingsDTO
    portfolio_risk: PortfolioRiskSettingsDTO | None = None
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
    status: Literal["queued", "succeeded", "failed"]


class BacktestRunStatusDTO(BaseModel):
    run_id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    started_at: str
    finished_at: str | None
    input_symbols: list[str]
    mode: Literal["backtest", "live"]
    result: BacktestResultDTO | None = None
    error: str | None = None


class LivePreflightResponseDTO(BaseModel):
    status: Literal["ok"] = "ok"
    message: str
    ready: bool = True
    reasons: list[str] = Field(default_factory=list)
    quote_summary: dict[str, str] | None = None
    quote_summaries: list[dict[str, str]] | None = None
    symbol_count: int = 1
    paper_result: BacktestResultDTO | None = None



def _default_runtime_risk() -> RiskSettingsDTO:
    return RiskSettingsDTO(
        max_position=Decimal("1"),
        max_notional=Decimal("100000"),
        max_order_size=Decimal("0.25"),
    )


def _default_runtime_backtest() -> BacktestSettingsDTO:
    return BacktestSettingsDTO(
        starting_cash=Decimal("10000"),
        fee_bps=Decimal("5"),
        trade_quantity=Decimal("0.1"),
    )


class LiveRuntimeStartRequestDTO(BaseModel):
    mode: Literal["live"] = "live"
    symbols: list[str] = Field(min_length=1)
    provider: Literal["mock", "csv", "kis"] = "mock"
    broker: Literal["paper", "kis"] = "paper"
    live_execution: Literal["paper", "live"] = "paper"
    risk: RiskSettingsDTO = Field(default_factory=_default_runtime_risk)
    portfolio_risk: PortfolioRiskSettingsDTO | None = None
    backtest: BacktestSettingsDTO = Field(default_factory=_default_runtime_backtest)
    strategy: StrategyConfigDTO | None = None


class LiveRuntimeStartResponseDTO(BaseModel):
    status: Literal["started"] = "started"
    session_id: str
    state: str
    started_at: str
    symbols: list[str]
    provider: str
    broker: str
    live_execution: Literal["paper", "live"]


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


# ---------------------------------------------------------------------------
# Dashboard DTOs
# ---------------------------------------------------------------------------


class DashboardStatusDTO(BaseModel):
    state: str
    last_heartbeat: str | None
    uptime_seconds: float | None
    controller_state: str | None = None
    session_id: str | None = None
    live_execution: str | None = None
    last_error: str | None = None
    provider: str | None = None
    symbols: list[str] | None = None
    market_session: str | None = None
    last_reconciliation_at: str | None = None
    last_reconciliation_status: str | None = None


class PositionDTO(BaseModel):
    symbol: str
    quantity: str
    average_cost: str
    unrealized_pnl: str | None = None


class PositionsResponseDTO(BaseModel):
    positions: list[PositionDTO]
    cash: str


class EventRecordDTO(BaseModel):
    event: str
    severity: str
    correlation_id: str
    timestamp: str
    payload: dict


class EventFeedDTO(BaseModel):
    events: list[EventRecordDTO]
    total: int


class ControlActionDTO(BaseModel):
    action: Literal["pause", "resume", "reset", "stop"]


class ControlResponseDTO(BaseModel):
    status: Literal["ok"]
    state: str


class TradeDTO(BaseModel):
    symbol: str
    entry_time: str
    exit_time: str
    entry_price: str
    exit_price: str
    quantity: str
    pnl: str
    holding_seconds: float


class TradeStatsDTO(BaseModel):
    trade_count: int
    win_rate: str
    risk_reward_ratio: str
    max_drawdown: str
    average_time_in_market_seconds: float


class TradeAnalyticsResponseDTO(BaseModel):
    stats: TradeStatsDTO
    trades: list[TradeDTO]


# ---------------------------------------------------------------------------
# Backtest run list DTOs (Phase 8)
# ---------------------------------------------------------------------------


class BacktestRunListItemDTO(BaseModel):
    run_id: str
    status: str
    started_at: str
    finished_at: str | None
    input_symbols: list[str]
    mode: str


class BacktestRunListResponseDTO(BaseModel):
    runs: list[BacktestRunListItemDTO]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Equity timeseries DTOs (Phase 8)
# ---------------------------------------------------------------------------


class EquityPointTimeseriesDTO(BaseModel):
    timestamp: str
    equity: str
    cash: str
    positions_value: str


class EquityTimeseriesDTO(BaseModel):
    session_id: str
    points: list[EquityPointTimeseriesDTO]
    total: int
