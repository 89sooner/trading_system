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
    assert settings.risk.max_notional == Decimal("100000.0")
    assert settings.backtest.fee_bps == Decimal("5.0")


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
