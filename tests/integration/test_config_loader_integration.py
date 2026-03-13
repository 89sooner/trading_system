from pathlib import Path

import pytest

from trading_system.config.settings import SettingsValidationError, load_settings


@pytest.mark.smoke
def test_load_settings_fails_when_nested_schema_key_is_missing(tmp_path: Path) -> None:
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
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(
        SettingsValidationError,
        match="Missing required key: 'backtest.trade_quantity'",
    ):
        load_settings(config_path)


@pytest.mark.extended
def test_load_settings_fails_when_nested_schema_type_is_invalid(tmp_path: Path) -> None:
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
  trade_quantity:
    amount: 0.1
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(
        SettingsValidationError,
        match="Invalid type for 'backtest.trade_quantity'",
    ):
        load_settings(config_path)
