from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from trading_system.api.errors import RequestValidationError
from trading_system.api.routes.analytics import router as analytics_router
from trading_system.api.routes.backtest import router as backtest_router
from trading_system.api.routes.dashboard import router as dashboard_router
from trading_system.api.routes.patterns import router as patterns_router
from trading_system.api.routes.strategies import router as strategies_router
from trading_system.api.schemas import ErrorResponseDTO
from trading_system.api.security import SecuritySettings, build_security_middleware
from trading_system.app.settings import SettingsValidationError as AppSettingsValidationError
from trading_system.config.settings import SettingsValidationError as ConfigSettingsValidationError


def create_app(live_loop=None) -> FastAPI:
    app = FastAPI(title="trading_system API", version="1.0.0")
    app.include_router(analytics_router)
    app.include_router(backtest_router)
    app.include_router(patterns_router)
    app.include_router(strategies_router)
    app.include_router(dashboard_router)

    # Make the live loop (if any) accessible from dashboard route dependencies
    app.state.live_loop = live_loop

    security_settings = SecuritySettings.from_env()
    app.middleware("http")(build_security_middleware(security_settings))

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

    return app
