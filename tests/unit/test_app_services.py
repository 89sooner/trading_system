from datetime import datetime, timezone
from decimal import Decimal

import pytest

from trading_system.app.services import build_services
from trading_system.app.settings import AppSettings


def test_build_services_uses_csv_provider_for_domestic_symbol(tmp_path, monkeypatch) -> None:
    csv_path = tmp_path / "005930.csv"
    csv_path.write_text(
        "timestamp,open,high,low,close,volume\n"
        "2024-01-02T00:00:00+00:00,70000,70500,69900,70400,1000\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("TRADING_SYSTEM_CSV_DIR", str(tmp_path))

    settings = AppSettings.from_cli(
        mode="backtest",
        symbols="005930",
        provider="csv",
        broker="paper",
        starting_cash="1000000",
        fee_bps="5",
        trade_quantity="1",
        max_position="10",
        max_notional="100000000",
        max_order_size="5",
    )
    settings.validate()

    services = build_services(settings)
    bars = list(services.data_provider.load_bars("005930"))

    assert bars[0].symbol == "005930"
    assert bars[0].close == Decimal("70400")
    assert bars[0].timestamp == datetime(2024, 1, 2, tzinfo=timezone.utc)


def test_build_services_raises_clear_error_when_csv_file_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TRADING_SYSTEM_CSV_DIR", str(tmp_path))

    settings = AppSettings.from_cli(
        mode="backtest",
        symbols="005930",
        provider="csv",
        broker="paper",
        starting_cash="1000000",
        fee_bps="5",
        trade_quantity="1",
        max_position="10",
        max_notional="100000000",
        max_order_size="5",
    )
    settings.validate()

    with pytest.raises(RuntimeError, match="missing: 005930"):
        build_services(settings)
