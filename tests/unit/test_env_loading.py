import os

from trading_system.config.env import load_runtime_env


def test_load_runtime_env_loads_default_dotenv(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TRADING_SYSTEM_KIS_APP_KEY", raising=False)
    monkeypatch.delenv("TRADING_SYSTEM_ENV_FILE", raising=False)
    (tmp_path / ".env").write_text(
        "TRADING_SYSTEM_KIS_APP_KEY=dotenv-app-key\n",
        encoding="utf-8",
    )

    loaded = load_runtime_env()

    assert loaded is True
    assert os.getenv("TRADING_SYSTEM_KIS_APP_KEY") == "dotenv-app-key"


def test_load_runtime_env_keeps_existing_environment_value(monkeypatch, tmp_path) -> None:
    env_file = tmp_path / "kis.env"
    env_file.write_text(
        "TRADING_SYSTEM_KIS_APP_SECRET=dotenv-secret\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("TRADING_SYSTEM_KIS_APP_SECRET", "process-secret")

    loaded = load_runtime_env(env_file)

    assert loaded is True
    assert os.getenv("TRADING_SYSTEM_KIS_APP_SECRET") == "process-secret"


def test_load_runtime_env_uses_configured_env_file(monkeypatch, tmp_path) -> None:
    env_file = tmp_path / "local-kis.env"
    env_file.write_text(
        "TRADING_SYSTEM_KIS_CANO=87654321\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("TRADING_SYSTEM_KIS_CANO", raising=False)
    monkeypatch.setenv("TRADING_SYSTEM_ENV_FILE", str(env_file))

    loaded = load_runtime_env()

    assert loaded is True
    assert os.getenv("TRADING_SYSTEM_KIS_CANO") == "87654321"
