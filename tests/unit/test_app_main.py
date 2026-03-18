from trading_system.app.main import run


def test_cli_backtest_mode_runs_successfully(capsys) -> None:
    exit_code = run(["--mode", "backtest", "--symbols", "BTCUSDT"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Smoke backtest result" in captured.out


def test_cli_live_mode_runs_preflight_when_api_key_is_present(capsys, monkeypatch) -> None:
    monkeypatch.setenv("TRADING_SYSTEM_API_KEY", "dummy-key")

    exit_code = run(["--mode", "live", "--symbols", "BTCUSDT"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Live mode preflight passed" in captured.out


def test_cli_live_mode_runs_paper_loop_when_requested(capsys, monkeypatch) -> None:
    monkeypatch.setenv("TRADING_SYSTEM_API_KEY", "dummy-key")

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
    assert "Smoke backtest result" in captured.out


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


def test_cli_returns_runtime_error_for_unsupported_multi_symbol_backtest(capsys) -> None:
    exit_code = run(["--mode", "backtest", "--symbols", "BTCUSDT,ETHUSDT"])

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "Runtime error:" in captured.err
    assert "supports exactly one symbol" in captured.err


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
    assert "--live-execution must be one of: 'preflight', 'paper'." in captured.err
