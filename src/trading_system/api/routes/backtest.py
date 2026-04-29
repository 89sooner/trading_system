import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, status

from trading_system.api.errors import RequestValidationError
from trading_system.api.schemas import (
    BacktestDispatcherStatusDTO,
    BacktestJobProgressDTO,
    BacktestJobSummaryDTO,
    BacktestResultDTO,
    BacktestRetentionPreviewDTO,
    BacktestRetentionPruneRequestDTO,
    BacktestRetentionPruneResponseDTO,
    BacktestRunAcceptedDTO,
    BacktestRunListItemDTO,
    BacktestRunListResponseDTO,
    BacktestRunRequestDTO,
    BacktestRunStatusDTO,
    LivePreflightRequestDTO,
    LivePreflightResponseDTO,
    ReadinessCheckDTO,
    RunMetadataDTO,
    StrategyConfigDTO,
    SymbolReadinessDTO,
)
from trading_system.app.services import PreflightCheckResult, build_services
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
from trading_system.backtest.dto import (
    BacktestResultDTO as SerializedBacktestResultDTO,
)
from trading_system.backtest.dto import (
    BacktestRunDTO,
    BacktestRunMetadataDTO,
)
from trading_system.backtest.engine import BacktestCancelled, BacktestResult
from trading_system.backtest.file_repository import FileBacktestRunRepository
from trading_system.backtest.jobs import (
    BacktestJobProgress,
    BacktestJobRecord,
    BacktestJobRepository,
)
from trading_system.backtest.repository import BacktestRunRepository
from trading_system.core.compat import UTC
from trading_system.execution.order_audit import (
    OrderAuditRepository,
    create_order_audit_repository,
)
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


def _create_job_repository() -> BacktestJobRepository:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        from trading_system.backtest.supabase_repository import SupabaseBacktestRunRepository
        return SupabaseBacktestRunRepository(database_url)
    return FileBacktestRunRepository(
        Path(os.getenv("TRADING_SYSTEM_RUNS_DIR", "data/runs"))
    )


_RUN_REPOSITORY = _create_run_repository()
_JOB_REPOSITORY = _create_job_repository()
_ORDER_AUDIT_REPOSITORY: OrderAuditRepository | None = create_order_audit_repository()
_MAX_FEE_BPS = Decimal("1000")
_PROGRESS_UPDATE_INTERVAL_SECONDS = 1.0
_PROGRESS_UPDATE_PERCENT_STEP = 1.0


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

    if (
        payload.mode == "live"
        and payload.provider == "kis"
        and payload.broker == "kis"
        and payload.live_execution == "live"
    ):
        _validate_kis_live_integer_quantity(
            "backtest.trade_quantity",
            payload.backtest.trade_quantity,
        )
        _validate_kis_live_integer_quantity(
            "risk.max_order_size",
            payload.risk.max_order_size,
        )
        _validate_kis_live_integer_quantity(
            "risk.max_position",
            payload.risk.max_position,
        )

    _validate_strategy_payload(payload.strategy)


def _validate_kis_live_integer_quantity(field_name: str, value: Decimal) -> None:
    if value != value.to_integral_value():
        raise RequestValidationError(
            error_code="invalid_kis_live_quantity",
            message=f"{field_name} must be an integer share quantity for KIS live orders.",
        )


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


def _to_live_preflight_response(result: PreflightCheckResult) -> LivePreflightResponseDTO:
    return LivePreflightResponseDTO(
        message=result.message,
        ready=result.ready,
        reasons=result.reasons,
        blocking_reasons=result.blocking_reasons,
        warnings=result.warnings,
        quote_summary=result.quote_summary,
        quote_summaries=result.quote_summaries,
        symbol_count=result.symbol_count,
        checks=[
            ReadinessCheckDTO(
                name=check.name,
                status=check.status,
                summary=check.summary,
                details=check.details,
            )
            for check in result.checks
        ],
        symbol_checks=[
            SymbolReadinessDTO(
                symbol=check.symbol,
                status=check.status,
                summary=check.summary,
                price=check.price,
                volume=check.volume,
            )
            for check in result.symbol_checks
        ],
        next_allowed_actions=result.next_allowed_actions,
        checked_at=result.checked_at,
    )


def _to_run_metadata(
    payload: BacktestRunRequestDTO,
    settings: AppSettings,
) -> BacktestRunMetadataDTO:
    requested_metadata = payload.metadata
    strategy = payload.strategy
    source = requested_metadata.source if requested_metadata is not None else None
    if source is None:
        source = "api"
    return BacktestRunMetadataDTO(
        provider=settings.provider,
        broker=settings.broker,
        strategy_profile_id=(strategy.profile_id if strategy is not None else None),
        pattern_set_id=(strategy.pattern_set_id if strategy is not None else None),
        source=source,
        requested_by=(requested_metadata.requested_by if requested_metadata is not None else None),
        notes=(requested_metadata.notes if requested_metadata is not None else None),
    )


def _to_api_run_metadata(
    metadata: BacktestRunMetadataDTO | None,
) -> RunMetadataDTO | None:
    if metadata is None:
        return None
    return RunMetadataDTO(
        provider=metadata.provider,
        broker=metadata.broker,
        strategy_profile_id=metadata.strategy_profile_id,
        pattern_set_id=metadata.pattern_set_id,
        source=metadata.source,
        requested_by=metadata.requested_by,
        notes=metadata.notes,
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


def _job_repository_factory() -> BacktestJobRepository:
    repo = _JOB_REPOSITORY
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
        return _create_job_repository()
    return repo


def _to_job_summary(job: BacktestJobRecord | None) -> BacktestJobSummaryDTO | None:
    if job is None:
        return None
    return BacktestJobSummaryDTO(
        worker_id=job.worker_id,
        lease_expires_at=job.lease_expires_at,
        last_heartbeat_at=job.last_heartbeat_at,
        attempt_count=job.attempt_count,
        max_attempts=job.max_attempts,
        cancel_requested=job.cancel_requested,
        progress=BacktestJobProgressDTO(
            processed_bars=job.progress.processed_bars,
            total_bars=job.progress.total_bars,
            percent=job.progress.percent,
            last_bar_timestamp=job.progress.last_bar_timestamp,
            updated_at=job.progress.updated_at,
        ),
    )


def _execute_backtest_run(item: QueuedBacktestRun) -> BacktestRunDTO:
    finished_at = datetime.now(UTC)
    try:
        assert isinstance(item.payload, AppSettings)
        services = build_services(
            item.payload,
            order_audit_repository=_ORDER_AUDIT_REPOSITORY,
        )
        result = services.run(audit_owner_id=item.run_id)
        return BacktestRunDTO.succeeded(
            run_id=item.run_id,
            started_at=item.started_at,
            finished_at=finished_at,
            input_symbols=item.input_symbols,
            mode=item.mode,
            metadata=item.metadata if isinstance(item.metadata, BacktestRunMetadataDTO) else None,
            result=result,
        )
    except Exception as exc:
        return BacktestRunDTO.failed(
            run_id=item.run_id,
            started_at=item.started_at,
            finished_at=finished_at,
            input_symbols=item.input_symbols,
            mode=item.mode,
            metadata=item.metadata if isinstance(item.metadata, BacktestRunMetadataDTO) else None,
            error=str(exc),
        )


def execute_backtest_job(
    job: BacktestJobRecord,
    worker_id: str,
    lease_seconds: int,
) -> BacktestRunDTO:
    run = _RUN_REPOSITORY.get(job.run_id)
    last_progress_update_at: datetime | None = None
    last_progress_percent = 0.0
    try:
        payload = BacktestRunRequestDTO.model_validate(job.payload)
        settings = _to_app_settings(payload)
        metadata = _to_run_metadata(payload, settings)
        started_at = run.started_at if run is not None else job.created_at
        _RUN_REPOSITORY.save(
            BacktestRunDTO.running(
                run_id=job.run_id,
                started_at=started_at,
                input_symbols=settings.symbols,
                mode=settings.mode.value,
                metadata=metadata,
            )
        )

        def _cancel_check() -> bool:
            current = _JOB_REPOSITORY.get_job(job.run_id)
            return current.cancel_requested if current is not None else False

        def _progress(processed: int, total: int, bar) -> None:
            nonlocal last_progress_percent, last_progress_update_at
            percent = (processed / total * 100.0) if total else 100.0
            current_time = datetime.now(UTC)
            now = current_time.isoformat().replace("+00:00", "Z")
            should_update = (
                processed >= total
                or last_progress_update_at is None
                or percent - last_progress_percent >= _PROGRESS_UPDATE_PERCENT_STEP
                or (
                    current_time - last_progress_update_at
                ).total_seconds()
                >= _PROGRESS_UPDATE_INTERVAL_SECONDS
            )
            if not should_update:
                return
            progress = BacktestJobProgress(
                processed_bars=processed,
                total_bars=total,
                percent=percent,
                last_bar_timestamp=bar.timestamp.isoformat().replace("+00:00", "Z"),
                updated_at=now,
            )
            _JOB_REPOSITORY.heartbeat(
                job.run_id,
                worker_id=worker_id,
                lease_seconds=lease_seconds,
            )
            _JOB_REPOSITORY.update_progress(job.run_id, progress, worker_id=worker_id)
            last_progress_update_at = current_time
            last_progress_percent = percent

        services = build_services(settings, order_audit_repository=_ORDER_AUDIT_REPOSITORY)
        result = services.run(
            audit_owner_id=job.run_id,
            progress_callback=_progress,
            cancel_check=_cancel_check,
        )
        final_run = BacktestRunDTO.succeeded(
            run_id=job.run_id,
            started_at=started_at,
            finished_at=datetime.now(UTC),
            input_symbols=settings.symbols,
            mode=settings.mode.value,
            metadata=metadata,
            result=result,
        )
        _RUN_REPOSITORY.save(final_run)
        _JOB_REPOSITORY.complete(job.run_id)
        return final_run
    except BacktestCancelled as exc:
        if run is None:
            payload_symbols: list[str] = []
            mode = "backtest"
            metadata = None
            started_at = job.created_at
        else:
            payload_symbols = run.input_symbols
            mode = run.mode
            metadata = run.metadata
            started_at = run.started_at
        final_run = BacktestRunDTO.cancelled(
            run_id=job.run_id,
            started_at=started_at,
            finished_at=datetime.now(UTC),
            input_symbols=payload_symbols,
            mode=mode,
            metadata=metadata,
            error=str(exc),
        )
        _RUN_REPOSITORY.save(final_run)
        _JOB_REPOSITORY.cancel(job.run_id, str(exc))
        return final_run
    except Exception as exc:
        if run is None:
            payload_symbols = []
            mode = "backtest"
            metadata = None
            started_at = job.created_at
        else:
            payload_symbols = run.input_symbols
            mode = run.mode
            metadata = run.metadata
            started_at = run.started_at
        final_run = BacktestRunDTO.failed(
            run_id=job.run_id,
            started_at=started_at,
            finished_at=datetime.now(UTC),
            input_symbols=payload_symbols,
            mode=mode,
            metadata=metadata,
            error=str(exc),
        )
        _RUN_REPOSITORY.save(final_run)
        _JOB_REPOSITORY.fail(job.run_id, str(exc))
        return final_run


def create_backtest_dispatcher() -> BacktestRunDispatcher:
    return BacktestRunDispatcher(
        repo_factory=_repository_factory,
        executor=_execute_backtest_run,
        job_repo_factory=_job_repository_factory,
        job_executor=execute_backtest_job,
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
            metadata=_to_api_run_metadata(r.metadata),
            job=_to_job_summary(_JOB_REPOSITORY.get_job(r.run_id)),
        )
        for r in runs
    ]
    return BacktestRunListResponseDTO(runs=items, total=total, page=page, page_size=page_size)


@router.get("/backtests/dispatcher", response_model=BacktestDispatcherStatusDTO)
def get_backtest_dispatcher_status(request: Request) -> BacktestDispatcherStatusDTO:
    dispatcher = getattr(request.app.state, "backtest_dispatcher", None)
    if dispatcher is None:
        return BacktestDispatcherStatusDTO(running=False, queue_depth=0, max_queue_size=0)
    snapshot = dispatcher.snapshot()
    return BacktestDispatcherStatusDTO(
        running=snapshot.running,
        queue_depth=snapshot.queue_depth,
        max_queue_size=snapshot.max_queue_size,
        durable_queued_count=snapshot.durable_queued_count,
        durable_running_count=snapshot.durable_running_count,
        durable_stale_count=snapshot.durable_stale_count,
        oldest_queued_age_seconds=snapshot.oldest_queued_age_seconds,
    )


@router.get("/backtests/retention/preview", response_model=BacktestRetentionPreviewDTO)
def preview_backtest_retention(
    cutoff: str,
    status: str | None = None,
) -> BacktestRetentionPreviewDTO:
    candidate_ids = _retention_candidate_ids(cutoff=cutoff, status=status)
    return BacktestRetentionPreviewDTO(
        cutoff=cutoff,
        status=status,
        candidate_count=len(candidate_ids),
        run_ids=candidate_ids,
    )


@router.post("/backtests/retention/prune", response_model=BacktestRetentionPruneResponseDTO)
def prune_backtest_retention(
    payload: BacktestRetentionPruneRequestDTO,
) -> BacktestRetentionPruneResponseDTO:
    if payload.confirm != "DELETE":
        raise RequestValidationError(
            error_code="retention_confirmation_required",
            message="confirm must be DELETE before pruning backtest runs.",
        )
    candidate_ids = _retention_candidate_ids(cutoff=payload.cutoff, status=payload.status)
    deleted_ids: list[str] = []
    for run_id in candidate_ids:
        if _RUN_REPOSITORY.delete(run_id):
            deleted_ids.append(run_id)
    return BacktestRetentionPruneResponseDTO(
        deleted_count=len(deleted_ids),
        run_ids=deleted_ids,
    )


def create_backtest_run(
    payload: BacktestRunRequestDTO,
    request: Request | None = None,
) -> BacktestRunAcceptedDTO:
    settings = _to_app_settings(payload)
    metadata = _to_run_metadata(payload, settings)
    run_id = str(uuid4())
    dispatcher = getattr(request.app.state, "backtest_dispatcher", None) if request else None
    queued_run = BacktestRunDTO.queued(
        run_id=run_id,
        started_at=datetime.now(UTC),
        input_symbols=settings.symbols,
        mode=settings.mode.value,
        metadata=metadata,
    )
    _RUN_REPOSITORY.save(queued_run)
    job = BacktestJobRecord.queued(
        run_id=run_id,
        payload=payload.model_dump(mode="json"),
        created_at=queued_run.started_at,
    )
    _JOB_REPOSITORY.enqueue(job)

    if dispatcher is None:
        claimed = _JOB_REPOSITORY.claim_next(
            worker_id="inline",
            lease_seconds=30,
        )
        final_run = execute_backtest_job(claimed or job, "inline", 30)
        return BacktestRunAcceptedDTO(run_id=run_id, status=final_run.status)

    dispatcher.submit(
        QueuedBacktestRun(
            run_id=run_id,
            started_at=queued_run.started_at,
            input_symbols=settings.symbols,
            mode=settings.mode.value,
            payload=settings,
            metadata=metadata,
        )
    )
    return BacktestRunAcceptedDTO(run_id=run_id, status="queued")


def _retention_candidate_ids(*, cutoff: str, status: str | None) -> list[str]:
    cutoff_dt = _parse_cutoff(cutoff)
    candidates: list[str] = []
    page = 1
    while True:
        runs, total = _RUN_REPOSITORY.list(page=page, page_size=100, status=status)
        if not runs:
            break
        for run in runs:
            run_dt = _parse_cutoff(run.started_at)
            if run_dt < cutoff_dt:
                candidates.append(run.run_id)
        if page * 100 >= total:
            break
        page += 1
    return candidates


def _parse_cutoff(value: str) -> datetime:
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise RequestValidationError(
            error_code="invalid_cutoff",
            message="cutoff must be an ISO 8601 datetime.",
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


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
        metadata=_to_api_run_metadata(run.metadata),
        result=_to_api_result_dto(run.result) if run.result is not None else None,
        error=run.error,
        job=_to_job_summary(_JOB_REPOSITORY.get_job(run.run_id)),
    )


@router.post("/backtests/{run_id}/cancel", response_model=BacktestRunStatusDTO)
def cancel_backtest_run(run_id: str) -> BacktestRunStatusDTO:
    run = _RUN_REPOSITORY.get(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backtest run not found")
    if run.status in {"succeeded", "failed", "cancelled"}:
        return get_backtest_run(run_id)
    job = _JOB_REPOSITORY.request_cancel(run_id)
    if run.status == "queued":
        cancelled = BacktestRunDTO.cancelled(
            run_id=run.run_id,
            started_at=run.started_at,
            finished_at=datetime.now(UTC),
            input_symbols=run.input_symbols,
            mode=run.mode,
            metadata=run.metadata,
        )
        _RUN_REPOSITORY.save(cancelled)
        _JOB_REPOSITORY.cancel(run_id, "Backtest cancelled before execution.")
    elif job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backtest job not found")
    return get_backtest_run(run_id)


@router.post("/live/preflight", response_model=LivePreflightResponseDTO)
def run_live_preflight(
    payload: LivePreflightRequestDTO,
    request: Request,
) -> LivePreflightResponseDTO:
    settings = _to_app_settings(payload)
    services = build_services(settings)
    result = services.preflight_live()
    controller = getattr(request.app.state, "live_runtime_controller", None)
    if controller is not None:
        controller.record_preflight(settings, result)
    return _to_live_preflight_response(result)
