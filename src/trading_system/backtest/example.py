from trading_system.app.backtest_demo import (
    SmokeBacktestConfig,
    build_sample_bars,
    format_result,
    run_smoke_backtest,
)

__all__ = [
    "SmokeBacktestConfig",
    "build_sample_bars",
    "run_smoke_backtest",
    "format_result",
]


def main() -> None:
    print(format_result(run_smoke_backtest()))


if __name__ == "__main__":
    main()
