from trading_system.app.main import run


def test_cli_backtest_mode_runs_successfully(capsys) -> None:
    exit_code = run(["--mode", "backtest", "--symbols", "BTCUSDT"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Smoke backtest result" in captured.out


def test_cli_live_mode_runs_preflight_when_api_key_is_present(
    capsys, monkeypatch
) -> None:
    monkeypatch.setenv("TRADING_SYSTEM_API_KEY", "dummy-key")

    exit_code = run(["--mode", "live", "--symbols", "BTCUSDT"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Live mode preflight passed" in captured.out


def test_cli_loads_dotenv_before_building_kis_services(
    capsys,
    monkeypatch,
    tmp_path,
) -> None:
    class _StubServicesKisClient:
        def preflight_symbol(self, symbol: str):
            class Quote:
                def __init__(self, quote_symbol: str) -> None:
                    self.symbol = quote_symbol
                    self.price = "70000"
                    self.volume = "1000"

            return Quote(symbol)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "TRADING_SYSTEM_KIS_APP_KEY=dotenv-app-key",
                "TRADING_SYSTEM_KIS_APP_SECRET=dotenv-app-secret",
                "TRADING_SYSTEM_KIS_CANO=12345678",
                "TRADING_SYSTEM_KIS_ACNT_PRDT_CD=01",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TRADING_SYSTEM_ENV_FILE", raising=False)
    monkeypatch.delenv("TRADING_SYSTEM_KIS_APP_KEY", raising=False)
    monkeypatch.delenv("TRADING_SYSTEM_KIS_APP_SECRET", raising=False)
    monkeypatch.delenv("TRADING_SYSTEM_KIS_CANO", raising=False)
    monkeypatch.delenv("TRADING_SYSTEM_KIS_ACNT_PRDT_CD", raising=False)

    def build_stub_client():
        import os

        assert os.getenv("TRADING_SYSTEM_KIS_APP_KEY") == "dotenv-app-key"
        assert os.getenv("TRADING_SYSTEM_KIS_APP_SECRET") == "dotenv-app-secret"
        return _StubServicesKisClient()

    monkeypatch.setattr(
        "trading_system.app.services.KisApiClient.from_env",
        build_stub_client,
    )

    exit_code = run(
        [
            "--mode",
            "live",
            "--symbols",
            "005930",
            "--provider",
            "kis",
            "--broker",
            "kis",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "KIS live preflight" in captured.out


def test_cli_live_mode_runs_paper_loop_when_requested(capsys, monkeypatch) -> None:
    monkeypatch.setenv("TRADING_SYSTEM_API_KEY", "dummy-key")

    import time

    def mock_sleep(_):
        raise KeyboardInterrupt()

    monkeypatch.setattr(time, "sleep", mock_sleep)

    exit_code = run(
        [
            "--mode",
            "live",
            "--symbols",
            "BTCUSDT",
            "--live-execution",
            "paper",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Live mode preflight passed" in captured.out


def test_cli_live_mode_fails_when_api_key_is_missing(capsys, monkeypatch) -> None:
    monkeypatch.delenv("TRADING_SYSTEM_API_KEY", raising=False)

    exit_code = run(["--mode", "live", "--symbols", "BTCUSDT"])

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "Runtime error:" in captured.err
    assert "Missing required secret: TRADING_SYSTEM_API_KEY" in captured.err


def test_cli_returns_validation_error_for_invalid_fee_bps(capsys) -> None:
    exit_code = run(["--mode", "backtest", "--fee-bps", "-1"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Configuration error:" in captured.err
    assert "--fee-bps must be between 0 and 1000." in captured.err


def test_cli_multi_symbol_backtest_runs_successfully(capsys) -> None:
    exit_code = run(["--mode", "backtest", "--symbols", "BTCUSDT,ETHUSDT"])

    assert exit_code == 0


def test_cli_accepts_strategy_profile_id(capsys) -> None:
    exit_code = run(
        [
            "--mode",
            "backtest",
            "--symbols",
            "BTCUSDT",
            "--strategy-profile-id",
            "sample_bullish_profile",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Smoke backtest result" in captured.out


def test_cli_accepts_yaml_config(capsys, tmp_path) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        """
app:
  environment: local
  timezone: Asia/Seoul
  mode: backtest
market_data:
  provider: mock
  symbols:
    - BTCUSDT
execution:
  broker: paper
risk:
  max_position: 1
  max_notional: 100000
  max_order_size: 0.25
backtest:
  starting_cash: 10000
  fee_bps: 5
  trade_quantity: 0.1
""".strip(),
        encoding="utf-8",
    )

    exit_code = run(["--config", str(config_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Smoke backtest result" in captured.out


def test_cli_returns_validation_error_for_unsupported_provider(capsys) -> None:
    exit_code = run(["--mode", "backtest", "--provider", "unknown"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Configuration error:" in captured.err
    assert "--provider must be one of: 'mock', 'csv', 'kis'." in captured.err


def test_cli_returns_validation_error_for_invalid_live_execution_mode(capsys) -> None:
    exit_code = run(["--mode", "live", "--live-execution", "invalid"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Configuration error:" in captured.err
    assert (
        "--live-execution must be one of: 'preflight', 'paper', 'live'." in captured.err
    )


def test_cli_live_mode_rejects_live_execution_without_opt_in(
    capsys, monkeypatch
) -> None:
    class _StubServicesKisClient:
        def preflight_symbol(self, symbol: str):
            class Quote:
                def __init__(self, quote_symbol: str) -> None:
                    self.symbol = quote_symbol
                    self.price = "70000"
                    self.volume = "1000"

            return Quote(symbol)

    monkeypatch.setattr(
        "trading_system.app.services.KisApiClient.from_env",
        lambda: _StubServicesKisClient(),
    )
    monkeypatch.setenv("TRADING_SYSTEM_ENABLE_LIVE_ORDERS", "false")

    exit_code = run(
        [
            "--mode",
            "live",
            "--symbols",
            "005930",
            "--provider",
            "kis",
            "--broker",
            "kis",
            "--live-execution",
            "live",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "Runtime error:" in captured.err
    assert "TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true" in captured.err
