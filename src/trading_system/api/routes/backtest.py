from decimal import Decimal
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from trading_system.api.errors import RequestValidationError
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
from trading_system.backtest.dto import BacktestResultDTO as SerializedBacktestResultDTO
from trading_system.backtest.dto import BacktestRunDTO
from trading_system.backtest.engine import BacktestResult
from trading_system.backtest.repository import InMemoryBacktestRunRepository

router = APIRouter(prefix="/api/v1", tags=["runtime"])

_RUN_REPOSITORY = InMemoryBacktestRunRepository()
_MAX_FEE_BPS = Decimal("1000")


def _validate_request_payload(payload: BacktestRunRequestDTO | LivePreflightRequestDTO) -> None:
    if len(payload.symbols) != 1:
        raise RequestValidationError(
            error_code="invalid_symbols",
            message="Exactly one symbol is required for this API runtime.",
        )

    normalized = payload.symbols[0].strip().upper()
    if not normalized or not normalized.replace("-", "").isalnum():
        raise RequestValidationError(
            error_code="invalid_symbols",
            message="Symbol must be non-empty and contain only letters, numbers, or '-'.",
        )

    if payload.backtest.trade_quantity <= 0:
        raise RequestValidationError(
            error_code="invalid_trade_quantity",
            message="trade_quantity must be greater than 0.",
        )

    if payload.backtest.fee_bps < 0 or payload.backtest.fee_bps > _MAX_FEE_BPS:
        raise RequestValidationError(
            error_code="invalid_fee_bps",
            message="fee_bps must be between 0 and 1000.",
        )


def _to_app_settings(payload: BacktestRunRequestDTO | LivePreflightRequestDTO) -> AppSettings:
    _validate_request_payload(payload)
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


def _to_serialized_result(result: BacktestResult) -> SerializedBacktestResultDTO:
    return SerializedBacktestResultDTO.from_result(result)


def _to_api_result_dto(result: SerializedBacktestResultDTO) -> BacktestResultDTO:
    return BacktestResultDTO(
        summary={
            "return": result.summary.return_value,
            "max_drawdown": result.summary.max_drawdown,
            "volatility": result.summary.volatility,
            "win_rate": result.summary.win_rate,
        },
        equity_curve=result.equity_curve,
        drawdown_curve=result.drawdown_curve,
        orders=result.orders,
        risk_rejections=result.risk_rejections,
    )


@router.post(
    "/backtests",
    response_model=BacktestRunAcceptedDTO,
    status_code=status.HTTP_201_CREATED,
)
def create_backtest_run(payload: BacktestRunRequestDTO) -> BacktestRunAcceptedDTO:
    settings = _to_app_settings(payload)
    run_id = str(uuid4())
    started_at = datetime.now(UTC)
    services = build_services(settings)
    result = services.run()
    finished_at = datetime.now(UTC)

    stored_run = BacktestRunDTO.succeeded(
        run_id=run_id,
        started_at=started_at,
        finished_at=finished_at,
        input_symbols=settings.symbols,
        mode=settings.mode.value,
        result=result,
    )
    _RUN_REPOSITORY.save(stored_run)
    return BacktestRunAcceptedDTO(run_id=run_id, status="succeeded")


@router.get("/backtests/{run_id}", response_model=BacktestRunStatusDTO)
def get_backtest_run(run_id: str) -> BacktestRunStatusDTO:
    run = _RUN_REPOSITORY.get(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backtest run not found")

    return BacktestRunStatusDTO(
        run_id=run.run_id,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        input_symbols=run.input_symbols,
        mode=run.mode,
        result=_to_api_result_dto(run.result) if run.result is not None else None,
        error=run.error,
    )


@router.post("/live/preflight", response_model=LivePreflightResponseDTO)
def run_live_preflight(payload: LivePreflightRequestDTO) -> LivePreflightResponseDTO:
    settings = _to_app_settings(payload)
    services = build_services(settings)
    message = services.preflight_live()
    paper_result = None
    if settings.live_execution == LiveExecutionMode.PAPER:
        paper_result = _to_api_result_dto(_to_serialized_result(services.run_live_paper()))
    return LivePreflightResponseDTO(message=message, paper_result=paper_result)
