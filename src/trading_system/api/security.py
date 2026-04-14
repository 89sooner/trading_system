from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Iterable

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from trading_system.config.settings import load_settings
from trading_system.core.ops import correlation_scope


@dataclass(slots=True)
class SecuritySettings:
    allowed_api_keys: tuple[str, ...]
    cors_allow_origins: tuple[str, ...]
    rate_limit_max_requests: int = 60
    rate_limit_window_seconds: int = 60

    @classmethod
    def from_env(cls) -> "SecuritySettings":
        from os import getenv

        raw_keys = getenv("TRADING_SYSTEM_ALLOWED_API_KEYS", "")
        raw_origins = getenv("TRADING_SYSTEM_CORS_ALLOW_ORIGINS", "")
        rate_limit_max = int(getenv("TRADING_SYSTEM_RATE_LIMIT_MAX_REQUESTS", "60"))
        rate_limit_window = int(getenv("TRADING_SYSTEM_RATE_LIMIT_WINDOW_SECONDS", "60"))
        config_origins = _load_cors_origins_from_config(getenv("TRADING_SYSTEM_CONFIG_PATH"))
        return cls(
            allowed_api_keys=_split_csv(raw_keys),
            cors_allow_origins=_split_csv(raw_origins) or config_origins,
            rate_limit_max_requests=max(1, rate_limit_max),
            rate_limit_window_seconds=max(1, rate_limit_window),
        )


@dataclass(slots=True)
class SimpleRateLimiter:
    max_requests: int
    window_seconds: int
    _requests: dict[str, deque[float]] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def allow(self, key: str, now: float | None = None) -> bool:
        current_time = time.time() if now is None else now
        threshold = current_time - self.window_seconds

        with self._lock:
            bucket = self._requests.setdefault(key, deque())
            while bucket and bucket[0] <= threshold:
                bucket.popleft()

            if len(bucket) >= self.max_requests:
                return False

            bucket.append(current_time)
            return True


def _split_csv(raw_value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in raw_value.split(",") if item.strip())


def _load_cors_origins_from_config(config_path: str | None) -> tuple[str, ...]:
    path = Path(config_path) if config_path else Path("configs/base.yaml")
    if not path.exists():
        return ("*",)
    return load_settings(path).api.cors_allow_origins


def _is_origin_allowed(origin: str | None, allowed_origins: Iterable[str]) -> bool:
    allowed = tuple(allowed_origins)
    return "*" in allowed or (origin is not None and origin in allowed)


def _cors_headers(origin: str | None, allowed_origins: Iterable[str]) -> dict[str, str]:
    if not _is_origin_allowed(origin, allowed_origins):
        return {}

    allow_origin = origin if origin is not None and "*" not in allowed_origins else "*"
    return {
        "Access-Control-Allow-Origin": allow_origin,
        "Access-Control-Allow-Headers": "Authorization,Content-Type,X-API-Key,X-Correlation-ID",
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    }


def _extract_api_key(request: Request) -> str | None:
    return request.headers.get("x-api-key") or request.headers.get("authorization")


def _is_auth_exempt_path(path: str) -> bool:
    return path == "/health" or path.startswith("/api/v1/admin/")


def build_security_middleware(settings: SecuritySettings, key_repository=None):
    limiter = SimpleRateLimiter(
        max_requests=settings.rate_limit_max_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )

    async def middleware(request: Request, call_next) -> Response:
        origin = request.headers.get("origin")
        cors_headers = _cors_headers(origin, settings.cors_allow_origins)

        if request.method == "OPTIONS":
            return Response(status_code=204, headers=cors_headers)

        request_key = request.headers.get("x-correlation-id")
        with correlation_scope(request_key):
            correlation_id = request.state.correlation_id = request_key or ""
            if not correlation_id:
                from trading_system.core.ops import get_or_create_correlation_id

                correlation_id = get_or_create_correlation_id()
                request.state.correlation_id = correlation_id

            is_auth_exempt = _is_auth_exempt_path(request.url.path)
            has_env_keys = bool(settings.allowed_api_keys)
            has_repo_keys = key_repository is not None and key_repository.has_any_keys()

            if not is_auth_exempt and (has_env_keys or has_repo_keys):
                is_sse_path = request.url.path == "/api/v1/dashboard/stream"
                if is_sse_path:
                    supplied_key = request.query_params.get("api_key")
                else:
                    supplied_key = _extract_api_key(request)
                valid = supplied_key in settings.allowed_api_keys
                if not valid and key_repository is not None:
                    valid = key_repository.is_valid_key(supplied_key)
                if not valid:
                    return JSONResponse(
                        status_code=401,
                        content={
                            "error_code": "auth_invalid_api_key",
                            "message": "Missing or invalid API key.",
                        },
                        headers={**cors_headers, "X-Correlation-ID": correlation_id},
                    )

            rate_key = f"{request.client.host if request.client else 'unknown'}:{request.url.path}"
            if not limiter.allow(rate_key):
                return JSONResponse(
                    status_code=429,
                    content={
                        "error_code": "rate_limit_exceeded",
                        "message": "Too many requests. Please retry later.",
                    },
                    headers={**cors_headers, "X-Correlation-ID": correlation_id},
                )

            response = await call_next(request)
            response.headers.update(cors_headers)
            response.headers["X-Correlation-ID"] = correlation_id
            return response

    return middleware
