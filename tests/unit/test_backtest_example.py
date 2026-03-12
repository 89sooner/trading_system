from decimal import Decimal

from trading_system.backtest.example import SmokeBacktestConfig, format_result, run_smoke_backtest


def test_run_smoke_backtest_produces_deterministic_result() -> None:
    result = run_smoke_backtest(
        SmokeBacktestConfig(
            starting_cash=Decimal("10000"),
            fee_bps=Decimal("5"),
            trade_quantity=Decimal("0.1"),
            max_position=Decimal("1.0"),
            max_notional=Decimal("100000"),
            max_order_size=Decimal("0.25"),
        )
    )

    assert result.processed_bars == 7
    assert result.executed_trades == 6
    assert result.rejected_signals == 0
    assert result.final_portfolio.cash == Decimal("9979.16910")
    assert result.final_portfolio.positions == {"BTCUSDT": Decimal("0.2")}
    assert result.equity_curve == [
        Decimal("10000"),
        Decimal("9999.99495"),
        Decimal("10000.18980"),
        Decimal("9999.98470"),
        Decimal("10000.17950"),
        Decimal("10000.37425"),
        Decimal("9999.76910"),
    ]
    assert result.total_return == Decimal("-0.00002309")


def test_format_result_includes_operational_summary() -> None:
    result = run_smoke_backtest()

    output = format_result(result)

    assert "Smoke backtest result" in output
    assert "processed_bars: 7" in output
    assert "positions: BTCUSDT=0.2" in output
