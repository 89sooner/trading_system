import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from trading_system.api.admin.repository import ApiKeyRepository
from trading_system.api.errors import RequestValidationError
from trading_system.api.routes import backtest as backtest_module
from trading_system.api.routes.admin import router as admin_router
from trading_system.api.routes.analytics import router as analytics_router
from trading_system.api.routes.backtest import router as backtest_router
from trading_system.api.routes.dashboard import router as dashboard_router
from trading_system.api.routes.live_runtime import router as live_runtime_router
from trading_system.api.routes.order_audit import router as order_audit_router
from trading_system.api.routes.patterns import router as patterns_router
from trading_system.api.routes.strategies import router as strategies_router
from trading_system.api.schemas import ErrorResponseDTO
from trading_system.api.security import SecuritySettings, build_security_middleware
from trading_system.app.live_runtime_controller import LiveRuntimeController
from trading_system.app.live_runtime_events import create_live_runtime_event_repository
from trading_system.app.live_runtime_history import create_live_runtime_session_repository
from trading_system.app.services import build_services
from trading_system.app.settings import SettingsValidationError as AppSettingsValidationError
from trading_system.config.settings import SettingsValidationError as ConfigSettingsValidationError
from trading_system.execution.order_audit import create_order_audit_repository

load_dotenv()


def create_app(live_loop=None) -> FastAPI:
    app = FastAPI(title='trading_system API', version='1.0.0')
    dispatcher = backtest_module.create_backtest_dispatcher()

    app.include_router(admin_router)
    app.include_router(analytics_router)
    app.include_router(backtest_router)
    app.include_router(live_runtime_router)
    app.include_router(order_audit_router)
    app.include_router(patterns_router)
    app.include_router(strategies_router)
    app.include_router(dashboard_router)

    app.state.live_loop = live_loop
    app.state.backtest_dispatcher = dispatcher
    app.state.live_runtime_history_repository = create_live_runtime_session_repository()
    app.state.live_runtime_event_repository = create_live_runtime_event_repository()
    app.state.order_audit_repository = create_order_audit_repository()
    backtest_module._ORDER_AUDIT_REPOSITORY = app.state.order_audit_repository
    app.state.live_runtime_controller = LiveRuntimeController(
        services_builder=lambda settings: build_services(
            settings,
            order_audit_repository=app.state.order_audit_repository,
        ),
        attach_loop=lambda loop: setattr(app.state, 'live_loop', loop),
        history_repository=app.state.live_runtime_history_repository,
        event_repository=app.state.live_runtime_event_repository,
    )

    api_keys_path = Path(os.getenv('TRADING_SYSTEM_API_KEYS_PATH') or 'data/api_keys.json')
    key_repository = ApiKeyRepository(api_keys_path)
    app.state.api_key_repository = key_repository

    security_settings = SecuritySettings.from_env()
    app.middleware('http')(build_security_middleware(security_settings, key_repository))

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        dispatcher.recover_interrupted_runs()
        dispatcher.start()
        try:
            yield
        finally:
            controller = getattr(app.state, 'live_runtime_controller', None)
            if controller is not None and controller.has_active_session():
                try:
                    controller.stop(requested_by='shutdown')
                except RuntimeError:
                    pass
            dispatcher.shutdown()

    app.router.lifespan_context = lifespan

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        body = ErrorResponseDTO(error_code=exc.error_code, message=str(exc))
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=body.model_dump())

    @app.exception_handler(AppSettingsValidationError)
    @app.exception_handler(ConfigSettingsValidationError)
    async def handle_settings_validation(
        _request: Request,
        exc: AppSettingsValidationError | ConfigSettingsValidationError,
    ) -> JSONResponse:
        body = ErrorResponseDTO(error_code='settings_validation_error', message=str(exc))
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=body.model_dump(),
        )

    @app.exception_handler(RuntimeError)
    async def handle_runtime_error(_request: Request, exc: RuntimeError) -> JSONResponse:
        body = ErrorResponseDTO(error_code='runtime_error', message=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=body.model_dump(),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, _exc: Exception) -> JSONResponse:
        body = ErrorResponseDTO(
            error_code='internal_server_error',
            message='An internal error occurred.',
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=body.model_dump(),
        )

    def _health_payload() -> dict:
        return {'status': 'ok'}

    @app.get('/health', include_in_schema=False)
    def root_health() -> dict:
        return _health_payload()

    @app.get('/api/v1/health', include_in_schema=False)
    def api_health() -> dict:
        return _health_payload()

    return app


app = create_app()
