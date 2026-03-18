from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from trading_system.core.compat import StrEnum


class AppMode(StrEnum):
    BACKTEST = "backtest"
    LIVE = "live"


class LiveExecutionMode(StrEnum):
    PREFLIGHT = "preflight"
    PAPER = "paper"


class SettingsValidationError(ValueError):
    """Raised when user-provided application settings are invalid."""


@dataclass(slots=True)
class RiskSettings:
    max_position: Decimal
    max_notional: Decimal
    max_order_size: Decimal


@dataclass(slots=True)
class BacktestSettings:
    starting_cash: Decimal
    fee_bps: Decimal
    trade_quantity: Decimal


@dataclass(slots=True)
class AppSettings:
    mode: AppMode
    symbols: tuple[str, ...]
    provider: str
    broker: str
    live_execution: LiveExecutionMode
    risk: RiskSettings
    backtest: BacktestSettings

    @classmethod
    def from_cli(
        cls,
        mode: str,
        symbols: str,
        provider: str,
        broker: str,
        live_execution: str,
        starting_cash: str,
        fee_bps: str,
        trade_quantity: str,
        max_position: str,
        max_notional: str,
        max_order_size: str,
    ) -> "AppSettings":
        parsed_symbols = tuple(
            symbol.strip().upper()
            for symbol in symbols.split(",")
            if symbol.strip()
        )
        try:
            parsed_mode = AppMode(mode)
        except ValueError as exc:
            raise SettingsValidationError(
                f"Unsupported mode '{mode}'. Allowed modes: {[item.value for item in AppMode]}."
            ) from exc

        return cls(
            mode=parsed_mode,
            symbols=parsed_symbols,
            provider=provider.strip().lower(),
            broker=broker.strip().lower(),
            live_execution=_parse_live_execution_mode(live_execution),
            risk=RiskSettings(
                max_position=_to_decimal(max_position, "max_position"),
                max_notional=_to_decimal(max_notional, "max_notional"),
                max_order_size=_to_decimal(max_order_size, "max_order_size"),
            ),
            backtest=BacktestSettings(
                starting_cash=_to_decimal(starting_cash, "starting_cash"),
                fee_bps=_to_decimal(fee_bps, "fee_bps"),
                trade_quantity=_to_decimal(trade_quantity, "trade_quantity"),
            ),
        )

    def validate(self) -> None:
        if not self.symbols:
            raise SettingsValidationError("At least one symbol is required via --symbols.")

        if self.provider not in {"mock", "csv", "kis"}:
            raise SettingsValidationError("--provider must be one of: 'mock', 'csv', 'kis'.")

        if self.broker not in {"paper", "kis"}:
            raise SettingsValidationError("--broker must be one of: 'paper', 'kis'.")

        if self.live_execution not in {LiveExecutionMode.PREFLIGHT, LiveExecutionMode.PAPER}:
            raise SettingsValidationError(
                "--live-execution must be one of: 'preflight', 'paper'."
            )

        if self.backtest.starting_cash <= 0:
            raise SettingsValidationError("--starting-cash must be greater than 0.")

        if self.backtest.trade_quantity <= 0:
            raise SettingsValidationError("--trade-quantity must be greater than 0.")

        if self.backtest.fee_bps < 0 or self.backtest.fee_bps > Decimal("1000"):
            raise SettingsValidationError("--fee-bps must be between 0 and 1000.")

        if self.risk.max_position <= 0:
            raise SettingsValidationError("--max-position must be greater than 0.")

        if self.risk.max_notional <= 0:
            raise SettingsValidationError("--max-notional must be greater than 0.")

        if self.risk.max_order_size <= 0:
            raise SettingsValidationError("--max-order-size must be greater than 0.")

        if self.risk.max_order_size > self.risk.max_position:
            raise SettingsValidationError("--max-order-size cannot exceed --max-position.")


def _to_decimal(value: str, field_name: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise SettingsValidationError(f"{field_name} must be a valid decimal value.") from exc


def _parse_live_execution_mode(value: str) -> LiveExecutionMode:
    normalized = value.strip().lower()
    try:
        return LiveExecutionMode(normalized)
    except ValueError as exc:
        raise SettingsValidationError(
            "--live-execution must be one of: 'preflight', 'paper'."
        ) from exc
