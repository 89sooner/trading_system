from __future__ import annotations

import csv
import io
import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import Response

from trading_system.api.errors import RequestValidationError
from trading_system.api.routes.backtest import _to_app_settings, _to_live_preflight_response
from trading_system.api.schemas import (
    EquityPointTimeseriesDTO,
    EquityTimeseriesDTO,
    LiveRuntimeEventRecordDTO,
    LiveRuntimeSessionEvidenceDTO,
    LiveRuntimeSessionListDTO,
    LiveRuntimeSessionRecordDTO,
    LiveRuntimeStartRequestDTO,
    LiveRuntimeStartResponseDTO,
    OrderAuditRecordDTO,
)
from trading_system.app.equity_writer import create_historical_equity_reader
from trading_system.app.live_runtime_events import LiveRuntimeEventFilter
from trading_system.app.live_runtime_history import (
    LiveRuntimeSessionFilter,
    LiveRuntimeSessionListResult,
)
from trading_system.app.services import build_services
from trading_system.core.compat import UTC
from trading_system.execution.order_audit import OrderAuditRecord

router = APIRouter(prefix='/api/v1/live/runtime', tags=['runtime'])


def _to_session_record_dto(record) -> LiveRuntimeSessionRecordDTO:
    return LiveRuntimeSessionRecordDTO(
        session_id=record.session_id,
        started_at=record.started_at,
        ended_at=record.ended_at,
        provider=record.provider,
        broker=record.broker,
        live_execution=record.live_execution,
        symbols=list(record.symbols),
        last_state=record.last_state,
        last_error=record.last_error,
        preflight_summary=record.preflight_summary,
    )


def _search_sessions(
    repo,
    query: LiveRuntimeSessionFilter,
) -> LiveRuntimeSessionListResult:
    if hasattr(repo, 'search'):
        return repo.search(query)
    records = repo.list(limit=query.page_size)
    return LiveRuntimeSessionListResult(
        records=records,
        total=len(records),
        page=query.page,
        page_size=query.page_size,
    )


def _query_from_params(
    *,
    limit: int | None = None,
    page: int = 1,
    page_size: int = 20,
    start: str | None = None,
    end: str | None = None,
    provider: str | None = None,
    broker: str | None = None,
    live_execution: str | None = None,
    state: str | None = None,
    symbol: str | None = None,
    has_error: bool | None = None,
    sort: str = 'desc',
) -> LiveRuntimeSessionFilter:
    _validate_datetime('start', start)
    _validate_datetime('end', end)
    if sort not in {'asc', 'desc'}:
        raise RequestValidationError(
            error_code='invalid_sort',
            message='sort must be one of: asc, desc.',
        )
    resolved_page_size = limit if limit is not None else page_size
    return LiveRuntimeSessionFilter(
        start=start,
        end=end,
        provider=provider,
        broker=broker,
        live_execution=live_execution,
        state=state,
        symbol=symbol,
        has_error=has_error,
        sort=sort,
        page=max(page, 1),
        page_size=max(1, min(resolved_page_size, 5000)),
    )


def _validate_datetime(name: str, value: str | None) -> None:
    if value is None or not value.strip():
        return
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise RequestValidationError(
            error_code=f'invalid_{name}',
            message=f'{name} must be an ISO 8601 datetime.',
        ) from exc
    if parsed.tzinfo is None:
        parsed.replace(tzinfo=UTC)


@router.post(
    '/start',
    response_model=LiveRuntimeStartResponseDTO,
    status_code=status.HTTP_201_CREATED,
)
def start_live_runtime(
    payload: LiveRuntimeStartRequestDTO,
    request: Request,
) -> LiveRuntimeStartResponseDTO:
    controller = getattr(request.app.state, 'live_runtime_controller', None)
    if controller is None:
        raise RuntimeError('Live runtime controller is unavailable.')
    if (
        getattr(request.app.state, 'live_loop', None) is not None
        and not controller.has_active_session()
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='An external live loop is already attached to this API process.',
        )
    if controller.has_active_session():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='A live runtime session is already active.',
        )

    settings = _to_app_settings(payload)
    preflight = build_services(settings).preflight_live()
    controller.record_preflight(settings, preflight)
    if not preflight.ready:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=preflight.message)

    session = controller.start(settings)
    return LiveRuntimeStartResponseDTO(
        status='started',
        session_id=session.session_id,
        state='starting',
        started_at=session.started_at,
        symbols=session.symbols,
        provider=session.provider,
        broker=session.broker,
        live_execution=session.live_execution,
        preflight=_to_live_preflight_response(preflight),
    )


@router.get('/sessions', response_model=LiveRuntimeSessionListDTO)
def list_live_runtime_sessions(
    request: Request,
    limit: int | None = None,
    page: int = 1,
    page_size: int = 20,
    start: str | None = None,
    end: str | None = None,
    provider: str | None = None,
    broker: str | None = None,
    live_execution: str | None = None,
    state: str | None = None,
    symbol: str | None = None,
    has_error: bool | None = None,
    sort: str = 'desc',
) -> LiveRuntimeSessionListDTO:
    repo = getattr(request.app.state, 'live_runtime_history_repository', None)
    if repo is None:
        return LiveRuntimeSessionListDTO(sessions=[], total=0, page=page, page_size=page_size)
    query = _query_from_params(
        limit=limit,
        page=page,
        page_size=page_size,
        start=start,
        end=end,
        provider=provider,
        broker=broker,
        live_execution=live_execution,
        state=state,
        symbol=symbol,
        has_error=has_error,
        sort=sort,
    )
    result = _search_sessions(repo, query)
    return LiveRuntimeSessionListDTO(
        sessions=[_to_session_record_dto(record) for record in result.records],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get('/sessions/export')
def export_live_runtime_sessions(
    request: Request,
    format: str = 'csv',
    limit: int = 1000,
    start: str | None = None,
    end: str | None = None,
    provider: str | None = None,
    broker: str | None = None,
    live_execution: str | None = None,
    state: str | None = None,
    symbol: str | None = None,
    has_error: bool | None = None,
    sort: str = 'desc',
) -> Response:
    export_format = format.strip().lower()
    if export_format not in {'csv', 'jsonl'}:
        return Response('format must be one of: csv, jsonl', status_code=400)
    repo = getattr(request.app.state, 'live_runtime_history_repository', None)
    query = _query_from_params(
        limit=limit,
        page=1,
        start=start,
        end=end,
        provider=provider,
        broker=broker,
        live_execution=live_execution,
        state=state,
        symbol=symbol,
        has_error=has_error,
        sort=sort,
    )
    result = _search_sessions(repo, query) if repo is not None else LiveRuntimeSessionListResult(
        records=[],
        total=0,
        page=1,
        page_size=query.page_size,
    )
    headers = {
        'X-Live-Session-Record-Count': str(len(result.records)),
        'X-Live-Session-Applied-Filters': json.dumps(
            {
                'start': start,
                'end': end,
                'provider': provider,
                'broker': broker,
                'live_execution': live_execution,
                'state': state,
                'symbol': symbol,
                'has_error': has_error,
                'sort': sort,
                'limit': query.page_size,
            },
            default=str,
        ),
    }
    if export_format == 'jsonl':
        body = '\n'.join(
            json.dumps(_to_session_record_dto(record).model_dump(), default=str)
            for record in result.records
        )
        if body:
            body += '\n'
        return Response(body, media_type='application/x-ndjson', headers=headers)
    return Response(_sessions_to_csv(result.records), media_type='text/csv', headers=headers)


@router.get('/sessions/{session_id}/equity', response_model=EquityTimeseriesDTO)
def get_live_runtime_session_equity(
    session_id: str,
    request: Request,
    limit: int = 300,
) -> EquityTimeseriesDTO:
    _require_session(session_id, request)
    reader = getattr(request.app.state, 'historical_equity_reader', None)
    if reader is None:
        reader = create_historical_equity_reader()
    points_data = reader.read_session(session_id, limit=max(1, min(limit, 5000)))
    points = [
        EquityPointTimeseriesDTO(
            timestamp=point['timestamp'],
            equity=point['equity'],
            cash=point['cash'],
            positions_value=point['positions_value'],
        )
        for point in points_data
    ]
    return EquityTimeseriesDTO(session_id=session_id, points=points, total=len(points))


@router.get('/sessions/{session_id}/evidence', response_model=LiveRuntimeSessionEvidenceDTO)
def get_live_runtime_session_evidence(
    session_id: str,
    request: Request,
    limit: int = 20,
) -> LiveRuntimeSessionEvidenceDTO:
    session = _require_session(session_id, request)
    resolved_limit = max(1, min(limit, 100))
    order_repo = getattr(request.app.state, 'order_audit_repository', None)
    order_records: list[OrderAuditRecord] = []
    order_count = 0
    if order_repo is not None:
        order_records = order_repo.list(
            scope='live_session',
            owner_id=session_id,
            sort='desc',
            limit=resolved_limit,
        )
        order_count = len(order_repo.list(
            scope='live_session',
            owner_id=session_id,
            sort='desc',
            limit=5000,
        ))

    event_repo = getattr(request.app.state, 'live_runtime_event_repository', None)
    archived_events = []
    archived_count = 0
    if event_repo is not None:
        archived_events = event_repo.list(
            LiveRuntimeEventFilter(session_id=session_id, sort='desc', limit=resolved_limit)
        )
        archived_count = len(event_repo.list(
            LiveRuntimeEventFilter(session_id=session_id, sort='desc', limit=5000)
        ))

    reader = getattr(request.app.state, 'historical_equity_reader', None)
    if reader is None:
        reader = create_historical_equity_reader()
    equity_points = reader.read_session(session_id, limit=5000)

    return LiveRuntimeSessionEvidenceDTO(
        session=_to_session_record_dto(session),
        order_audit_count=order_count,
        recent_order_audit_records=[_to_order_audit_dto(record) for record in order_records],
        equity_point_count=len(equity_points),
        archived_event_count=archived_count,
        recent_archived_events=[_to_event_dto(record) for record in archived_events],
    )


@router.get('/sessions/{session_id}', response_model=LiveRuntimeSessionRecordDTO)
def get_live_runtime_session(session_id: str, request: Request) -> LiveRuntimeSessionRecordDTO:
    return _to_session_record_dto(_require_session(session_id, request))


def _require_session(session_id: str, request: Request):
    repo = getattr(request.app.state, 'live_runtime_history_repository', None)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Live runtime session not found.',
        )
    record = repo.get(session_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Live runtime session not found.',
        )
    return record


def _to_event_dto(record) -> LiveRuntimeEventRecordDTO:
    return LiveRuntimeEventRecordDTO(
        record_id=record.record_id,
        session_id=record.session_id,
        event=record.event,
        severity=record.severity,
        correlation_id=record.correlation_id,
        timestamp=record.timestamp,
        payload=record.payload,
    )


def _to_order_audit_dto(record: OrderAuditRecord) -> OrderAuditRecordDTO:
    return OrderAuditRecordDTO(
        record_id=record.record_id,
        scope=record.scope,
        owner_id=record.owner_id,
        event=record.event,
        symbol=record.symbol,
        side=record.side,
        requested_quantity=record.requested_quantity,
        filled_quantity=record.filled_quantity,
        price=record.price,
        status=record.status,
        reason=record.reason,
        timestamp=record.timestamp,
        payload=record.payload,
        broker_order_id=record.broker_order_id,
    )


def _sessions_to_csv(records) -> str:
    output = io.StringIO()
    fieldnames = [
        'session_id',
        'started_at',
        'ended_at',
        'provider',
        'broker',
        'live_execution',
        'symbols',
        'last_state',
        'last_error',
        'preflight_summary',
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for record in records:
        writer.writerow({
            'session_id': record.session_id,
            'started_at': record.started_at,
            'ended_at': record.ended_at,
            'provider': record.provider,
            'broker': record.broker,
            'live_execution': record.live_execution,
            'symbols': ','.join(record.symbols),
            'last_state': record.last_state,
            'last_error': record.last_error,
            'preflight_summary': json.dumps(record.preflight_summary, default=str),
        })
    return output.getvalue()
