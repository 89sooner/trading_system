from trading_system.app.main import run


def test_cli_backtest_mode_runs_successfully(capsys) -> None:
    exit_code = run(["--mode", "backtest", "--symbols", "BTCUSDT"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Smoke backtest result" in captured.out


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
