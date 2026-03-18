from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from trading_system.api.routes.backtest import router as backtest_router
from trading_system.api.schemas import ErrorResponseDTO
from trading_system.app.settings import SettingsValidationError as AppSettingsValidationError
from trading_system.config.settings import SettingsValidationError as ConfigSettingsValidationError


def create_app() -> FastAPI:
    app = FastAPI(title="trading_system API", version="1.0.0")
    app.include_router(backtest_router)

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
