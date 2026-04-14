from trading_system.api.security import _is_auth_exempt_path


def test_health_path_is_auth_exempt() -> None:
    assert _is_auth_exempt_path("/health") is True


def test_admin_paths_remain_auth_exempt() -> None:
    assert _is_auth_exempt_path("/api/v1/admin/keys") is True


def test_runtime_paths_still_require_auth() -> None:
    assert _is_auth_exempt_path("/api/v1/backtests") is False
