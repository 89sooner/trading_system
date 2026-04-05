from decimal import Decimal

import pytest

from trading_system.config.settings import SettingsValidationError, load_settings


def test_load_settings_parses_base_schema(tmp_path) -> None:
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
    - btcusdt
execution:
  broker: paper
risk:
  max_position: 1.0
  max_notional: 100000.0
  max_order_size: 0.25
backtest:
  starting_cash: 10000.0
  fee_bps: 5.0
  trade_quantity: 0.1
""".strip(),
        encoding="utf-8",
    )

    settings = load_settings(config_path)

    assert settings.app.environment == "local"
    assert settings.market_data.symbols == ("BTCUSDT",)
    assert settings.execution.broker == "paper"
    assert settings.risk.max_notional == Decimal("100000.0")
    assert settings.backtest.fee_bps == Decimal("5.0")
    assert settings.app.reconciliation_interval is None
    assert settings.portfolio_risk is None


def test_load_settings_parses_reconciliation_interval_and_portfolio_risk(tmp_path) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        """
app:
  environment: local
  timezone: Asia/Seoul
  mode: live
  reconciliation_interval: 120
market_data:
  provider: kis
  symbols:
    - 005930
execution:
  broker: kis
risk:
  max_position: 10
  max_notional: 100000000
  max_order_size: 5
portfolio_risk:
  max_daily_drawdown_pct: 0.05
  sl_pct: 0.02
  tp_pct: 0.04
backtest:
  starting_cash: 10000000
  fee_bps: 5
  trade_quantity: 1
""".strip(),
        encoding="utf-8",
    )

    settings = load_settings(config_path)

    assert settings.app.reconciliation_interval == 120
    assert settings.portfolio_risk is not None
    assert settings.portfolio_risk.max_daily_drawdown_pct == Decimal("0.05")
    assert settings.portfolio_risk.sl_pct == Decimal("0.02")
    assert settings.portfolio_risk.tp_pct == Decimal("0.04")


def test_load_settings_rejects_invalid_reconciliation_interval(tmp_path) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        """
app:
  environment: local
  timezone: Asia/Seoul
  mode: live
  reconciliation_interval: 0
market_data:
  provider: kis
  symbols:
    - 005930
execution:
  broker: kis
risk:
  max_position: 10
  max_notional: 100000000
  max_order_size: 5
backtest:
  starting_cash: 10000000
  fee_bps: 5
  trade_quantity: 1
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(SettingsValidationError, match="app.reconciliation_interval"):
        load_settings(config_path)


def test_load_settings_rejects_invalid_portfolio_risk_drawdown(tmp_path) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        """
app:
  environment: local
  timezone: Asia/Seoul
  mode: live
market_data:
  provider: kis
  symbols:
    - 005930
execution:
  broker: kis
risk:
  max_position: 10
  max_notional: 100000000
  max_order_size: 5
portfolio_risk:
  max_daily_drawdown_pct: 1
backtest:
  starting_cash: 10000000
  fee_bps: 5
  trade_quantity: 1
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(SettingsValidationError, match="portfolio_risk.max_daily_drawdown_pct"):
        load_settings(config_path)


def test_load_settings_reports_missing_required_key(tmp_path) -> None:
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
  max_position: 1.0
  max_order_size: 0.25
backtest:
  starting_cash: 10000.0
  fee_bps: 5.0
  trade_quantity: 0.1
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(SettingsValidationError, match="Missing required key: 'risk.max_notional'"):
        load_settings(config_path)


def test_load_settings_reports_invalid_type(tmp_path) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        """
app:
  environment: local
  timezone: Asia/Seoul
  mode: backtest
market_data:
  provider: mock
  symbols: BTCUSDT
execution:
  broker: paper
risk:
  max_position: 1.0
  max_notional: 100000.0
  max_order_size: 0.25
backtest:
  starting_cash: 10000.0
  fee_bps: 5.0
  trade_quantity: 0.1
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(SettingsValidationError, match="Invalid type for 'market_data.symbols'"):
        load_settings(config_path)


def test_load_settings_reports_out_of_range_value(tmp_path) -> None:
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
  max_position: 1.0
  max_notional: 100000.0
  max_order_size: 0.25
backtest:
  starting_cash: 10000.0
  fee_bps: 1001
  trade_quantity: 0.1
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(SettingsValidationError, match="backtest.fee_bps"):
        load_settings(config_path)


def test_load_settings_reports_missing_execution_section(tmp_path) -> None:
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
risk:
  max_position: 1.0
  max_notional: 100000.0
  max_order_size: 0.25
backtest:
  starting_cash: 10000.0
  fee_bps: 5.0
  trade_quantity: 0.1
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(SettingsValidationError, match="Missing required key: 'execution'"):
        load_settings(config_path)


def test_load_settings_reports_invalid_execution_broker(tmp_path) -> None:
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
  broker: unknown
risk:
  max_position: 1.0
  max_notional: 100000.0
  max_order_size: 0.25
backtest:
  starting_cash: 10000.0
  fee_bps: 5.0
  trade_quantity: 0.1
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(SettingsValidationError, match="Invalid value for 'execution.broker'"):
        load_settings(config_path)


def test_load_settings_parses_kis_execution_broker(tmp_path) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        """
app:
  environment: local
  timezone: Asia/Seoul
  mode: live
market_data:
  provider: kis
  symbols:
    - 005930
execution:
  broker: kis
risk:
  max_position: 10
  max_notional: 100000000
  max_order_size: 5
backtest:
  starting_cash: 10000000
  fee_bps: 5
  trade_quantity: 1
""".strip(),
        encoding="utf-8",
    )

    settings = load_settings(config_path)
    assert settings.execution.broker == "kis"
