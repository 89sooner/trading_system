from trading_system.api.security import SecuritySettings, _cors_headers, _is_auth_exempt_path


def test_health_path_is_auth_exempt() -> None:
    assert _is_auth_exempt_path("/health") is True
    assert _is_auth_exempt_path("/api/v1/health") is True


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


def test_cors_origin_trailing_slash_is_normalized(monkeypatch) -> None:
    monkeypatch.setenv("TRADING_SYSTEM_ENV", "production")
    monkeypatch.setenv("TRADING_SYSTEM_CORS_ALLOW_ORIGINS", "https://app.example.com/")

    settings = SecuritySettings.from_env()

    assert settings.cors_allow_origins == ("https://app.example.com",)
    headers = _cors_headers("https://app.example.com", settings.cors_allow_origins)
    assert headers["Access-Control-Allow-Origin"] == "https://app.example.com"


def test_cors_origin_wildcard_pattern_matches_preview_domains(monkeypatch) -> None:
    monkeypatch.setenv("TRADING_SYSTEM_ENV", "production")
    monkeypatch.setenv("TRADING_SYSTEM_CORS_ALLOW_ORIGINS", "https://*.vercel.app")

    settings = SecuritySettings.from_env()

    headers = _cors_headers(
        "https://trading-system-git-main-user.vercel.app",
        settings.cors_allow_origins,
    )
    assert headers["Access-Control-Allow-Origin"] == (
        "https://trading-system-git-main-user.vercel.app"
    )
    assert _cors_headers("https://example.com", settings.cors_allow_origins) == {}
