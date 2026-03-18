from dataclasses import dataclass
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from trading_system.api.schemas import (
    BacktestResultDTO,
    BacktestRunAcceptedDTO,
    BacktestRunRequestDTO,
    BacktestRunStatusDTO,
    LivePreflightRequestDTO,
    LivePreflightResponseDTO,
)
from trading_system.app.services import build_services
from trading_system.app.settings import (
    AppMode,
    AppSettings,
    BacktestSettings,
    LiveExecutionMode,
    RiskSettings,
)
from trading_system.backtest.engine import BacktestResult

router = APIRouter(prefix="/api/v1", tags=["runtime"])


@dataclass(slots=True)
class StoredRun:
    status: str
    result: BacktestResult | None = None
    error: str | None = None


_RUNS: dict[str, StoredRun] = {}


def _to_app_settings(payload: BacktestRunRequestDTO | LivePreflightRequestDTO) -> AppSettings:
    settings = AppSettings(
        mode=AppMode(payload.mode),
        symbols=tuple(symbol.strip().upper() for symbol in payload.symbols if symbol.strip()),
        provider=payload.provider,
        broker=payload.broker,
        live_execution=LiveExecutionMode(payload.live_execution),
        risk=RiskSettings(
            max_position=payload.risk.max_position,
            max_notional=payload.risk.max_notional,
            max_order_size=payload.risk.max_order_size,
        ),
        backtest=BacktestSettings(
            starting_cash=payload.backtest.starting_cash,
            fee_bps=payload.backtest.fee_bps,
            trade_quantity=payload.backtest.trade_quantity,
        ),
    )
    settings.validate()
    return settings


def _to_result_dto(result: BacktestResult) -> BacktestResultDTO:
    return BacktestResultDTO(
        processed_bars=result.processed_bars,
        executed_trades=result.executed_trades,
        rejected_signals=result.rejected_signals,
        cash=result.final_portfolio.cash,
        positions=dict(result.final_portfolio.positions),
        total_return=result.total_return,
        equity_curve=result.equity_curve,
    )


@router.post(
    "/backtests",
    response_model=BacktestRunAcceptedDTO,
    status_code=status.HTTP_201_CREATED,
)
def create_backtest_run(payload: BacktestRunRequestDTO) -> BacktestRunAcceptedDTO:
    settings = _to_app_settings(payload)
    run_id = str(uuid4())
    services = build_services(settings)
    result = services.run()
    _RUNS[run_id] = StoredRun(status="succeeded", result=result)
    return BacktestRunAcceptedDTO(run_id=run_id, status="succeeded")


@router.get("/backtests/{run_id}", response_model=BacktestRunStatusDTO)
def get_backtest_run(run_id: str) -> BacktestRunStatusDTO:
    run = _RUNS.get(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backtest run not found")

    result_dto = _to_result_dto(run.result) if run.result is not None else None
    return BacktestRunStatusDTO(
        run_id=run_id,
        status=run.status,
        result=result_dto,
        error=run.error,
    )


@router.post("/live/preflight", response_model=LivePreflightResponseDTO)
def run_live_preflight(payload: LivePreflightRequestDTO) -> LivePreflightResponseDTO:
    settings = _to_app_settings(payload)
    services = build_services(settings)
    message = services.preflight_live()
    paper_result = None
    if settings.live_execution == LiveExecutionMode.PAPER:
        paper_result = _to_result_dto(services.run_live_paper())
    return LivePreflightResponseDTO(message=message, paper_result=paper_result)
