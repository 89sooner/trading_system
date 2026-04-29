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


class RunMetadataRequestDTO(BaseModel):
    source: str | None = None
    requested_by: str | None = None
    notes: str | None = None


class RunMetadataDTO(BaseModel):
    provider: str | None = None
    broker: str | None = None
    strategy_profile_id: str | None = None
    pattern_set_id: str | None = None
    source: str | None = None
    requested_by: str | None = None
    notes: str | None = None


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
    metadata: RunMetadataRequestDTO | None = None


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


class BacktestDispatcherStatusDTO(BaseModel):
    running: bool
    queue_depth: int
    max_queue_size: int
    durable_queued_count: int = 0
    durable_running_count: int = 0
    durable_stale_count: int = 0
    oldest_queued_age_seconds: float | None = None


class BacktestRetentionPreviewDTO(BaseModel):
    cutoff: str
    status: str | None = None
    candidate_count: int
    run_ids: list[str]


class BacktestRetentionPruneRequestDTO(BaseModel):
    cutoff: str
    status: str | None = None
    confirm: str | None = None


class BacktestRetentionPruneResponseDTO(BaseModel):
    deleted_count: int
    run_ids: list[str]


class BacktestRunStatusDTO(BaseModel):
    run_id: str
    status: Literal["queued", "running", "succeeded", "failed", "cancelled"]
    started_at: str
    finished_at: str | None
    input_symbols: list[str]
    mode: Literal["backtest", "live"]
    metadata: RunMetadataDTO | None = None
    result: BacktestResultDTO | None = None
    error: str | None = None
    job: "BacktestJobSummaryDTO | None" = None


class LivePreflightResponseDTO(BaseModel):
    status: Literal["ok"] = "ok"
    message: str
    ready: bool = True
    reasons: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    quote_summary: dict[str, str] | None = None
    quote_summaries: list[dict[str, str]] | None = None
    symbol_count: int = 1
    checks: list["ReadinessCheckDTO"] = Field(default_factory=list)
    symbol_checks: list["SymbolReadinessDTO"] = Field(default_factory=list)
    next_allowed_actions: list[str] = Field(default_factory=list)
    checked_at: str | None = None
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
    preflight: LivePreflightResponseDTO | None = None


class LiveRuntimeSessionRecordDTO(BaseModel):
    session_id: str
    started_at: str
    ended_at: str | None
    provider: str
    broker: str
    live_execution: str
    symbols: list[str]
    last_state: str
    last_error: str | None = None
    preflight_summary: dict | None = None


class LiveRuntimeSessionListDTO(BaseModel):
    sessions: list[LiveRuntimeSessionRecordDTO]
    total: int
    page: int = 1
    page_size: int = 20


class LiveRuntimeEventRecordDTO(BaseModel):
    record_id: str
    session_id: str
    event: str
    severity: str
    correlation_id: str
    timestamp: str
    payload: dict


class LiveRuntimeSessionEvidenceDTO(BaseModel):
    session: LiveRuntimeSessionRecordDTO
    order_audit_count: int
    recent_order_audit_records: list["OrderAuditRecordDTO"] = Field(default_factory=list)
    equity_point_count: int
    archived_event_count: int
    recent_archived_events: list[LiveRuntimeEventRecordDTO] = Field(default_factory=list)


class OrderAuditRecordDTO(BaseModel):
    record_id: str
    scope: Literal["backtest", "live_session"] | str
    owner_id: str
    event: str
    symbol: str | None = None
    side: str | None = None
    requested_quantity: str | None = None
    filled_quantity: str | None = None
    price: str | None = None
    status: str | None = None
    reason: str | None = None
    timestamp: str
    payload: dict
    broker_order_id: str | None = None


class OrderAuditListDTO(BaseModel):
    records: list[OrderAuditRecordDTO]
    total: int


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


class ReadinessCheckDTO(BaseModel):
    name: str
    status: Literal["pass", "warn", "fail"]
    summary: str
    details: dict[str, str] | None = None


class SymbolReadinessDTO(BaseModel):
    symbol: str
    status: Literal["pass", "warn", "fail"]
    summary: str
    price: str | None = None
    volume: str | None = None


class LastPreflightDTO(BaseModel):
    checked_at: str
    ready: bool
    message: str
    provider: str
    broker: str
    symbols: list[str]
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_allowed_actions: list[str] = Field(default_factory=list)


class DashboardIncidentDTO(BaseModel):
    event: str
    severity: str
    timestamp: str
    summary: str


class DashboardStatusDTO(BaseModel):
    state: str
    last_heartbeat: str | None
    uptime_seconds: float | None
    controller_state: str | None = None
    controller_state_detail: str | None = None
    active: bool = False
    session_id: str | None = None
    live_execution: str | None = None
    last_error: str | None = None
    provider: str | None = None
    broker: str | None = None
    symbols: list[str] | None = None
    market_session: str | None = None
    last_reconciliation_at: str | None = None
    last_reconciliation_status: str | None = None
    stop_supported: bool = False
    last_preflight: LastPreflightDTO | None = None
    latest_incident: DashboardIncidentDTO | None = None


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
    metadata: RunMetadataDTO | None = None
    job: "BacktestJobSummaryDTO | None" = None


class BacktestRunListResponseDTO(BaseModel):
    runs: list[BacktestRunListItemDTO]
    total: int
    page: int
    page_size: int


class BacktestJobProgressDTO(BaseModel):
    processed_bars: int = 0
    total_bars: int = 0
    percent: float = 0.0
    last_bar_timestamp: str | None = None
    updated_at: str | None = None


class BacktestJobSummaryDTO(BaseModel):
    worker_id: str | None = None
    lease_expires_at: str | None = None
    last_heartbeat_at: str | None = None
    attempt_count: int = 0
    max_attempts: int = 0
    cancel_requested: bool = False
    progress: BacktestJobProgressDTO = Field(default_factory=BacktestJobProgressDTO)


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


LivePreflightResponseDTO.model_rebuild()
BacktestRunStatusDTO.model_rebuild()
BacktestRunListItemDTO.model_rebuild()
LiveRuntimeSessionEvidenceDTO.model_rebuild()
