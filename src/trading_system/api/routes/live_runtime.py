from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from trading_system.api.routes.backtest import _to_app_settings, _to_live_preflight_response
from trading_system.api.schemas import (
    LiveRuntimeSessionListDTO,
    LiveRuntimeSessionRecordDTO,
    LiveRuntimeStartRequestDTO,
    LiveRuntimeStartResponseDTO,
)
from trading_system.app.services import build_services

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
def list_live_runtime_sessions(request: Request, limit: int = 20) -> LiveRuntimeSessionListDTO:
    repo = getattr(request.app.state, 'live_runtime_history_repository', None)
    if repo is None:
        return LiveRuntimeSessionListDTO(sessions=[], total=0)
    records = repo.list(limit=max(1, min(limit, 100)))
    return LiveRuntimeSessionListDTO(
        sessions=[_to_session_record_dto(record) for record in records],
        total=len(records),
    )


@router.get('/sessions/{session_id}', response_model=LiveRuntimeSessionRecordDTO)
def get_live_runtime_session(session_id: str, request: Request) -> LiveRuntimeSessionRecordDTO:
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
    return _to_session_record_dto(record)
