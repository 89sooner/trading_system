"""Unit tests for SSE /stream endpoint."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import trading_system.api.routes.dashboard as dashboard_module
from trading_system.api.server import create_app

_STREAM_PATH = "/api/v1/dashboard/stream"


@pytest.fixture(autouse=True)
def reset_sse_counter():
    """Reset the SSE connection counter before each test."""
    original = dashboard_module._active_sse_connections
    dashboard_module._active_sse_connections = 0
    yield
    dashboard_module._active_sse_connections = original


def _make_client(api_key: str = "") -> TestClient:
    """Create a full app client with security middleware active."""
    import os
    import tempfile

    empty_keys = tempfile.mktemp(suffix=".json")
    with open(empty_keys, "w") as f:
        f.write("[]")

    os.environ["TRADING_SYSTEM_API_KEYS_PATH"] = empty_keys
    os.environ["TRADING_SYSTEM_ALLOWED_API_KEYS"] = api_key
    app = create_app()
    return TestClient(app, raise_server_exceptions=False)


def test_sse_connection_limit_returns_429():
    dashboard_module._active_sse_connections = dashboard_module._MAX_SSE_CONNECTIONS
    client = _make_client(api_key="")
    response = client.get(_STREAM_PATH)
    assert response.status_code == 429


def test_sse_unauthorized_with_api_key_set():
    client = _make_client(api_key="secret-key")
    # No api_key query param → middleware returns 401
    response = client.get(_STREAM_PATH)
    assert response.status_code == 401


def test_sse_unauthorized_wrong_key():
    client = _make_client(api_key="secret-key")
    response = client.get(f"{_STREAM_PATH}?api_key=wrong-key")
    assert response.status_code == 401


def test_sse_valid_key_passes_auth():
    """Valid query-param api_key should pass middleware auth."""
    # Set connections to MAX so we get 429 instead of blocking on the stream.
    # This confirms auth passed (would be 401 otherwise).
    dashboard_module._active_sse_connections = dashboard_module._MAX_SSE_CONNECTIONS
    client = _make_client(api_key="my-key")
    response = client.get(f"{_STREAM_PATH}?api_key=my-key")
    # Auth passed → gets to connection limit → 429 (not 401)
    assert response.status_code == 429


def test_sse_no_api_key_configured_allows_connection():
    """No configured keys → no auth enforced → connection limit is the gate."""
    # 0 connections, no key configured → would stream (but we can't easily
    # test the infinite stream here; 429/401 absence confirms auth is open)
    dashboard_module._active_sse_connections = dashboard_module._MAX_SSE_CONNECTIONS
    client = _make_client(api_key="")
    response = client.get(_STREAM_PATH)
    # No auth gate → connection limit fires → 429 (not 401)
    assert response.status_code == 429
