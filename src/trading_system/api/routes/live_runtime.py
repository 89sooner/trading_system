from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from trading_system.api.routes.backtest import _to_app_settings
from trading_system.api.schemas import LiveRuntimeStartRequestDTO, LiveRuntimeStartResponseDTO
from trading_system.app.services import build_services

router = APIRouter(prefix='/api/v1/live/runtime', tags=['runtime'])


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
    )
