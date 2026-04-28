import argparse
import sys

from trading_system.app.backtest_demo import format_result
from trading_system.app.services import build_services
from trading_system.app.settings import (
    AppMode,
    AppSettings,
    LiveExecutionMode,
    SettingsValidationError,
)
from trading_system.config.env import load_runtime_env
from trading_system.config.settings import load_app_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Trading system application entrypoint")
    parser.add_argument("--config", default=None, help="YAML config path")
    parser.add_argument("--mode", default="backtest", help="Runtime mode (backtest|live)")
    parser.add_argument("--symbols", default="BTCUSDT", help="Comma-separated symbols")
    parser.add_argument("--provider", default="mock", help="Market data provider")
    parser.add_argument("--broker", default="paper", help="Execution broker")
    parser.add_argument(
        "--live-execution",
        default="preflight",
        help="Live execution mode (preflight|paper)",
    )
    parser.add_argument("--starting-cash", default="10000", help="Starting cash for backtest")
    parser.add_argument("--fee-bps", default="5", help="Fee in basis points")
    parser.add_argument("--trade-quantity", default="0.1", help="Per-trade quantity")
    parser.add_argument("--max-position", default="1.0", help="Risk max position")
    parser.add_argument("--max-notional", default="100000", help="Risk max notional")
    parser.add_argument("--max-order-size", default="0.25", help="Risk max order size")
    parser.add_argument("--strategy-profile-id", default=None, help="Stored strategy profile id")
    return parser


def run(argv: list[str] | None = None) -> int:
    load_runtime_env()

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        settings = (
            load_app_settings(args.config)
            if args.config is not None
            else AppSettings.from_cli(
                mode=args.mode,
                symbols=args.symbols,
                provider=args.provider,
                broker=args.broker,
                live_execution=args.live_execution,
                starting_cash=args.starting_cash,
                fee_bps=args.fee_bps,
                trade_quantity=args.trade_quantity,
                max_position=args.max_position,
                max_notional=args.max_notional,
                max_order_size=args.max_order_size,
                strategy_profile_id=args.strategy_profile_id,
            )
        )
        settings.validate()

        services = build_services(settings)
        if settings.mode == AppMode.LIVE:
            print(services.preflight_live())
            if settings.live_execution == LiveExecutionMode.PAPER:
                services.run_live_paper()
                print("Live paper execution loop ended.")
            if settings.live_execution == LiveExecutionMode.LIVE:
                services.run_live_execution()
                print("Live execution loop ended.")
            return 0

        result = services.run()
        print(format_result(result))
        return 0
    except SettingsValidationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"Runtime error: {exc}", file=sys.stderr)
        return 3


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
