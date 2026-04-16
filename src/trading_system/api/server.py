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
from trading_system.api.routes.patterns import router as patterns_router
from trading_system.api.routes.strategies import router as strategies_router
from trading_system.api.schemas import ErrorResponseDTO
from trading_system.api.security import SecuritySettings, build_security_middleware
from trading_system.app.settings import SettingsValidationError as AppSettingsValidationError
from trading_system.config.settings import SettingsValidationError as ConfigSettingsValidationError

load_dotenv()


def create_app(live_loop=None) -> FastAPI:
    dispatcher = backtest_module.create_backtest_dispatcher()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.backtest_dispatcher = dispatcher
        dispatcher.recover_interrupted_runs()
        dispatcher.start()
        try:
            yield
        finally:
            dispatcher.shutdown()

    app = FastAPI(title="trading_system API", version="1.0.0", lifespan=lifespan)
    app.include_router(admin_router)
    app.include_router(analytics_router)
    app.include_router(backtest_router)
    app.include_router(patterns_router)
    app.include_router(strategies_router)
    app.include_router(dashboard_router)

    # Make the live loop (if any) accessible from dashboard route dependencies
    app.state.live_loop = live_loop

    api_keys_path = Path(os.getenv("TRADING_SYSTEM_API_KEYS_PATH") or "data/api_keys.json")
    key_repository = ApiKeyRepository(api_keys_path)
    app.state.api_key_repository = key_repository

    security_settings = SecuritySettings.from_env()
    app.middleware("http")(build_security_middleware(security_settings, key_repository))
    app.state.backtest_dispatcher = dispatcher

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
        body = ErrorResponseDTO(error_code="settings_validation_error", message=str(exc))
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=body.model_dump(),
        )

    @app.exception_handler(RuntimeError)
    async def handle_runtime_error(_request: Request, exc: RuntimeError) -> JSONResponse:
        body = ErrorResponseDTO(error_code="runtime_error", message=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=body.model_dump(),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, _exc: Exception) -> JSONResponse:
        body = ErrorResponseDTO(
            error_code="internal_server_error",
            message="An internal error occurred.",
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=body.model_dump(),
        )

    @app.get("/health", include_in_schema=False)
    def health() -> dict:
        return {"status": "ok"}

    return app


# Module-level instance for uvicorn's "module:app" invocation style,
# e.g. `uvicorn trading_system.api.server:app`.
app = create_app()
