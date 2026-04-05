from decimal import Decimal
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
execution:
  broker: paper
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
execution:
  broker: paper
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


@pytest.mark.extended
def test_load_settings_supports_phase6_yaml_parity_fields(tmp_path: Path) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        """
app:
  environment: local
  timezone: Asia/Seoul
  mode: live
  reconciliation_interval: 180
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
  max_daily_drawdown_pct: 0.03
  sl_pct: 0.02
backtest:
  starting_cash: 10000000
  fee_bps: 5
  trade_quantity: 1
api:
  cors_allow_origins:
    - "http://localhost:3000"
""".strip(),
        encoding="utf-8",
    )

    settings = load_settings(config_path)

    assert settings.app.reconciliation_interval == 180
    assert settings.portfolio_risk is not None
    assert settings.portfolio_risk.max_daily_drawdown_pct == Decimal("0.03")
    assert settings.portfolio_risk.sl_pct == Decimal("0.02")
