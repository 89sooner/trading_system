import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, status

from trading_system.api.errors import RequestValidationError
from trading_system.api.schemas import (
    BacktestResultDTO,
    BacktestRunAcceptedDTO,
    BacktestRunListItemDTO,
    BacktestRunListResponseDTO,
    BacktestRunRequestDTO,
    BacktestRunStatusDTO,
    LivePreflightRequestDTO,
    LivePreflightResponseDTO,
    StrategyConfigDTO,
)
from trading_system.app.services import build_services
from trading_system.app.settings import (
    AppMode,
    AppSettings,
    BacktestSettings,
    LiveExecutionMode,
    PatternSignalStrategySettings,
    PortfolioRiskSettings,
    RiskSettings,
)
from trading_system.backtest.dispatcher import BacktestRunDispatcher, QueuedBacktestRun
from trading_system.backtest.dto import BacktestResultDTO as SerializedBacktestResultDTO
from trading_system.backtest.dto import BacktestRunDTO
from trading_system.backtest.engine import BacktestResult
from trading_system.backtest.file_repository import FileBacktestRunRepository
from trading_system.backtest.repository import BacktestRunRepository
from trading_system.core.compat import UTC
from trading_system.strategy.base import SignalSide

router = APIRouter(prefix="/api/v1", tags=["runtime"])


def _create_run_repository() -> BacktestRunRepository:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        from trading_system.backtest.supabase_repository import SupabaseBacktestRunRepository
        return SupabaseBacktestRunRepository(database_url)
    return FileBacktestRunRepository(
        Path(os.getenv("TRADING_SYSTEM_RUNS_DIR", "data/runs"))
    )


_RUN_REPOSITORY = _create_run_repository()
_MAX_FEE_BPS = Decimal("1000")


def _validate_request_payload(payload: BacktestRunRequestDTO | LivePreflightRequestDTO) -> None:
    for symbol in payload.symbols:
        normalized = symbol.strip().upper()
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

    _validate_strategy_payload(payload.strategy)


def _validate_strategy_payload(strategy: StrategyConfigDTO | None) -> None:
    if strategy is None:
        return
    if strategy.profile_id is not None:
        if (
            strategy.pattern_set_id is not None
            or strategy.label_to_side
            or strategy.threshold_overrides
        ):
            raise RequestValidationError(
                error_code="invalid_strategy",
                message=(
                    "strategy.profile_id cannot be combined with inline pattern strategy fields."
                ),
            )
        return

    if strategy.pattern_set_id is None or not strategy.pattern_set_id.strip():
        raise RequestValidationError(
            error_code="invalid_strategy",
            message="strategy.pattern_set_id is required for inline pattern strategy runs.",
        )

    if not strategy.label_to_side:
        raise RequestValidationError(
            error_code="invalid_strategy",
            message="strategy.label_to_side must contain at least one mapping.",
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
        portfolio_risk=(
            PortfolioRiskSettings(
                max_daily_drawdown_pct=payload.portfolio_risk.max_daily_drawdown_pct,
                sl_pct=payload.portfolio_risk.sl_pct,
                tp_pct=payload.portfolio_risk.tp_pct,
            )
            if payload.portfolio_risk is not None
            else None
        ),
        backtest=BacktestSettings(
            starting_cash=payload.backtest.starting_cash,
            fee_bps=payload.backtest.fee_bps,
            trade_quantity=payload.backtest.trade_quantity,
        ),
        strategy=_to_strategy_settings(payload.strategy),
    )
    settings.validate()
    return settings


def _to_strategy_settings(
    strategy: StrategyConfigDTO | None,
) -> PatternSignalStrategySettings | None:
    if strategy is None:
        return None
    return PatternSignalStrategySettings(
        type=strategy.type,
        profile_id=strategy.profile_id,
        pattern_set_id=strategy.pattern_set_id,
        label_to_side={
            label: SignalSide(side) for label, side in sorted(strategy.label_to_side.items())
        },
        trade_quantity=strategy.trade_quantity,
        threshold_overrides={
            label: float(threshold)
            for label, threshold in sorted(strategy.threshold_overrides.items())
        },
    )


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
        equity_curve=[
            {"timestamp": point.timestamp, "equity": point.equity} for point in result.equity_curve
        ],
        drawdown_curve=[
            {"timestamp": point.timestamp, "drawdown": point.drawdown}
            for point in result.drawdown_curve
        ],
        signals=[{"event": event.event, "payload": event.payload} for event in result.signals],
        orders=[{"event": event.event, "payload": event.payload} for event in result.orders],
        risk_rejections=[
            {"event": event.event, "payload": event.payload} for event in result.risk_rejections
        ],
    )


def _repository_factory() -> BacktestRunRepository:
    repo = _RUN_REPOSITORY
    if isinstance(repo, FileBacktestRunRepository):
        return repo
    try:
        from trading_system.backtest.supabase_repository import SupabaseBacktestRunRepository
    except Exception:
        SupabaseBacktestRunRepository = None  # type: ignore[assignment]
    if (
        SupabaseBacktestRunRepository is not None
        and isinstance(repo, SupabaseBacktestRunRepository)
    ):
        return _create_run_repository()
    return repo


def _execute_backtest_run(item: QueuedBacktestRun) -> BacktestRunDTO:
    finished_at = datetime.now(UTC)
    try:
        assert isinstance(item.payload, AppSettings)
        services = build_services(item.payload)
        result = services.run()
        return BacktestRunDTO.succeeded(
            run_id=item.run_id,
            started_at=item.started_at,
            finished_at=finished_at,
            input_symbols=item.input_symbols,
            mode=item.mode,
            result=result,
        )
    except Exception as exc:
        return BacktestRunDTO.failed(
            run_id=item.run_id,
            started_at=item.started_at,
            finished_at=finished_at,
            input_symbols=item.input_symbols,
            mode=item.mode,
            error=str(exc),
        )


def create_backtest_dispatcher() -> BacktestRunDispatcher:
    return BacktestRunDispatcher(
        repo_factory=_repository_factory,
        executor=_execute_backtest_run,
    )


@router.get("/backtests", response_model=BacktestRunListResponseDTO)
def list_backtest_runs(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    mode: str | None = None,
) -> BacktestRunListResponseDTO:
    page_size = max(1, min(page_size, 100))
    runs, total = _RUN_REPOSITORY.list(page=page, page_size=page_size, status=status, mode=mode)
    items = [
        BacktestRunListItemDTO(
            run_id=r.run_id,
            status=r.status,
            started_at=r.started_at,
            finished_at=r.finished_at,
            input_symbols=r.input_symbols,
            mode=r.mode,
        )
        for r in runs
    ]
    return BacktestRunListResponseDTO(runs=items, total=total, page=page, page_size=page_size)


def create_backtest_run(
    payload: BacktestRunRequestDTO,
    request: Request | None = None,
) -> BacktestRunAcceptedDTO:
    settings = _to_app_settings(payload)
    run_id = str(uuid4())
    dispatcher = getattr(request.app.state, "backtest_dispatcher", None) if request else None
    queued_run = BacktestRunDTO.queued(
        run_id=run_id,
        started_at=datetime.now(UTC),
        input_symbols=settings.symbols,
        mode=settings.mode.value,
    )
    _RUN_REPOSITORY.save(queued_run)

    item = QueuedBacktestRun(
        run_id=run_id,
        started_at=queued_run.started_at,
        input_symbols=settings.symbols,
        mode=settings.mode.value,
        payload=settings,
    )

    if dispatcher is None:
        final_run = _execute_backtest_run(item)
        _RUN_REPOSITORY.save(final_run)
        return BacktestRunAcceptedDTO(run_id=run_id, status=final_run.status)

    dispatcher.submit(item)
    return BacktestRunAcceptedDTO(run_id=run_id, status="queued")


@router.post(
    "/backtests",
    response_model=BacktestRunAcceptedDTO,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_backtest_run_endpoint(
    payload: BacktestRunRequestDTO,
    request: Request,
) -> BacktestRunAcceptedDTO:
    return create_backtest_run(payload, request)


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
    result = services.preflight_live()
    return LivePreflightResponseDTO(
        message=result.message,
        ready=result.ready,
        reasons=result.reasons,
        quote_summary=result.quote_summary,
        quote_summaries=result.quote_summaries,
        symbol_count=result.symbol_count,
    )
