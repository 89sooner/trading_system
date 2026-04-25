from trading_system.api.security import SecuritySettings, _cors_headers, _is_auth_exempt_path


def test_health_path_is_auth_exempt() -> None:
    assert _is_auth_exempt_path("/health") is True


def test_admin_paths_remain_auth_exempt() -> None:
    assert _is_auth_exempt_path("/api/v1/admin/keys") is True


def test_runtime_paths_still_require_auth() -> None:
    assert _is_auth_exempt_path("/api/v1/backtests") is False


def test_local_environment_appends_loopback_cors_origins(monkeypatch) -> None:
    monkeypatch.setenv("TRADING_SYSTEM_ENV", "local")
    monkeypatch.setenv("TRADING_SYSTEM_CORS_ALLOW_ORIGINS", "https://app.example.com")

    settings = SecuritySettings.from_env()

    assert settings.cors_allow_origins == (
        "https://app.example.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )
    headers = _cors_headers("http://localhost:3000", settings.cors_allow_origins)
    assert headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert "X-API-Key" in headers["Access-Control-Allow-Headers"]


def test_production_environment_does_not_append_local_cors_origins(monkeypatch) -> None:
    monkeypatch.setenv("TRADING_SYSTEM_ENV", "production")
    monkeypatch.setenv("TRADING_SYSTEM_CORS_ALLOW_ORIGINS", "https://app.example.com")

    settings = SecuritySettings.from_env()

    assert settings.cors_allow_origins == ("https://app.example.com",)
    assert _cors_headers("http://localhost:3000", settings.cors_allow_origins) == {}
