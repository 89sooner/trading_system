from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml

from trading_system.core.compat import StrEnum


class SettingsValidationError(ValueError):
    """Raised when configuration input is missing or invalid."""


class AppMode(StrEnum):
    BACKTEST = "backtest"
    LIVE = "live"


@dataclass(slots=True)
class AppSettings:
    environment: str
    timezone: str
    mode: AppMode
    reconciliation_interval: int | None = None


@dataclass(slots=True)
class MarketDataSettings:
    provider: str
    symbols: tuple[str, ...]


@dataclass(slots=True)
class RiskSettings:
    max_position: Decimal
    max_notional: Decimal
    max_order_size: Decimal


@dataclass(slots=True)
class PortfolioRiskSettings:
    max_daily_drawdown_pct: Decimal
    sl_pct: Decimal | None = None
    tp_pct: Decimal | None = None


@dataclass(slots=True)
class BacktestSettings:
    starting_cash: Decimal
    fee_bps: Decimal
    trade_quantity: Decimal


@dataclass(slots=True)
class StrategySettings:
    type: str = "pattern_signal"
    profile_id: str | None = None
    pattern_set_id: str | None = None
    label_to_side: dict[str, str] | None = None
    trade_quantity: Decimal | None = None
    threshold_overrides: dict[str, float] | None = None


@dataclass(slots=True)
class ExecutionSettings:
    broker: str


@dataclass(slots=True)
class ApiSettings:
    cors_allow_origins: tuple[str, ...]


@dataclass(slots=True)
class Settings:
    app: AppSettings
    market_data: MarketDataSettings
    execution: ExecutionSettings
    risk: RiskSettings
    portfolio_risk: PortfolioRiskSettings | None
    backtest: BacktestSettings
    strategy: StrategySettings | None
    api: ApiSettings


REQUIRED_ROOT_KEYS = ("app", "market_data", "execution", "risk", "backtest")


def load_settings(path: str | Path) -> Settings:
    config_path = Path(path)
    if not config_path.exists():
        raise SettingsValidationError(f"Configuration file not found: {config_path}")

    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise SettingsValidationError(f"Failed to parse YAML in {config_path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise SettingsValidationError("Configuration root must be a mapping.")

    for key in REQUIRED_ROOT_KEYS:
        _require_key(payload, key, path=key)

    app_section = _as_dict(payload["app"], "app")
    market_data_section = _as_dict(payload["market_data"], "market_data")
    execution_section = _as_dict(payload["execution"], "execution")
    risk_section = _as_dict(payload["risk"], "risk")
    backtest_section = _as_dict(payload["backtest"], "backtest")
    api_section = _as_dict(payload.get("api", {}), "api")
    portfolio_risk_section = _as_optional_dict(payload.get("portfolio_risk"), "portfolio_risk")
    strategy_section = _as_optional_dict(payload.get("strategy"), "strategy")

    settings = Settings(
        app=AppSettings(
            environment=_as_non_empty_str(
                _require_key(app_section, "environment", "app.environment"),
                "app.environment",
            ),
            timezone=_as_non_empty_str(
                _require_key(app_section, "timezone", "app.timezone"),
                "app.timezone",
            ),
            mode=_as_mode(
                _require_key(app_section, "mode", "app.mode"),
                "app.mode",
            ),
            reconciliation_interval=_as_optional_int(
                app_section.get("reconciliation_interval"),
                "app.reconciliation_interval",
                minimum=1,
            ),
        ),
        market_data=MarketDataSettings(
            provider=_as_non_empty_str(
                _require_key(market_data_section, "provider", "market_data.provider"),
                "market_data.provider",
            ),
            symbols=_as_symbols(
                _require_key(market_data_section, "symbols", "market_data.symbols"),
                "market_data.symbols",
            ),
        ),
        execution=ExecutionSettings(
            broker=_as_execution_broker(
                _require_key(execution_section, "broker", "execution.broker"),
                "execution.broker",
            ),
        ),
        risk=RiskSettings(
            max_position=_as_decimal(
                _require_key(risk_section, "max_position", "risk.max_position"),
                "risk.max_position",
                minimum=Decimal("0"),
            ),
            max_notional=_as_decimal(
                _require_key(risk_section, "max_notional", "risk.max_notional"),
                "risk.max_notional",
                minimum=Decimal("0"),
            ),
            max_order_size=_as_decimal(
                _require_key(risk_section, "max_order_size", "risk.max_order_size"),
                "risk.max_order_size",
                minimum=Decimal("0"),
            ),
        ),
        portfolio_risk=(
            PortfolioRiskSettings(
                max_daily_drawdown_pct=_as_decimal(
                    _require_key(
                        portfolio_risk_section,
                        "max_daily_drawdown_pct",
                        "portfolio_risk.max_daily_drawdown_pct",
                    ),
                    "portfolio_risk.max_daily_drawdown_pct",
                    minimum=Decimal("0"),
                    maximum=Decimal("1"),
                ),
                sl_pct=_as_optional_decimal(
                    portfolio_risk_section.get("sl_pct"),
                    "portfolio_risk.sl_pct",
                    minimum=Decimal("0"),
                ),
                tp_pct=_as_optional_decimal(
                    portfolio_risk_section.get("tp_pct"),
                    "portfolio_risk.tp_pct",
                    minimum=Decimal("0"),
                ),
            )
            if portfolio_risk_section is not None
            else None
        ),
        backtest=BacktestSettings(
            starting_cash=_as_decimal(
                _require_key(backtest_section, "starting_cash", "backtest.starting_cash"),
                "backtest.starting_cash",
                minimum=Decimal("0"),
            ),
            fee_bps=_as_decimal(
                _require_key(backtest_section, "fee_bps", "backtest.fee_bps"),
                "backtest.fee_bps",
                minimum=Decimal("0"),
                maximum=Decimal("1000"),
            ),
            trade_quantity=_as_decimal(
                _require_key(backtest_section, "trade_quantity", "backtest.trade_quantity"),
                "backtest.trade_quantity",
                minimum=Decimal("0"),
            ),
        ),
        strategy=_parse_strategy_settings(strategy_section),
        api=ApiSettings(
            cors_allow_origins=_as_non_empty_str_list(
                api_section.get("cors_allow_origins", ["*"]),
                "api.cors_allow_origins",
            ),
        ),
    )

    if settings.risk.max_order_size > settings.risk.max_position:
        raise SettingsValidationError(
            "Invalid value for 'risk.max_order_size': "
            "must be less than or equal to 'risk.max_position'."
        )

    if settings.portfolio_risk is not None:
        if settings.portfolio_risk.max_daily_drawdown_pct >= Decimal("1"):
            raise SettingsValidationError(
                "Invalid value for 'portfolio_risk.max_daily_drawdown_pct': must be less than 1."
            )

    return settings


def load_app_settings(path: str | Path):
    settings = load_settings(path)
    from trading_system.app.settings import (
        AppMode as RuntimeAppMode,
    )
    from trading_system.app.settings import (
        AppSettings as RuntimeAppSettings,
    )
    from trading_system.app.settings import (
        BacktestSettings as RuntimeBacktestSettings,
    )
    from trading_system.app.settings import (
        LiveExecutionMode,
        PatternSignalStrategySettings,
    )
    from trading_system.app.settings import (
        PortfolioRiskSettings as RuntimePortfolioRiskSettings,
    )
    from trading_system.app.settings import (
        RiskSettings as RuntimeRiskSettings,
    )
    from trading_system.strategy.base import SignalSide

    strategy = None
    if settings.strategy is not None:
        strategy = PatternSignalStrategySettings(
            type=settings.strategy.type,
            profile_id=settings.strategy.profile_id,
            pattern_set_id=settings.strategy.pattern_set_id,
            label_to_side={
                label: SignalSide(side)
                for label, side in (settings.strategy.label_to_side or {}).items()
            },
            trade_quantity=settings.strategy.trade_quantity,
            threshold_overrides=settings.strategy.threshold_overrides or {},
        )

    return RuntimeAppSettings(
        mode=RuntimeAppMode(settings.app.mode.value),
        symbols=settings.market_data.symbols,
        provider=settings.market_data.provider,
        broker=settings.execution.broker,
        live_execution=LiveExecutionMode.PREFLIGHT,
        risk=RuntimeRiskSettings(
            max_position=settings.risk.max_position,
            max_notional=settings.risk.max_notional,
            max_order_size=settings.risk.max_order_size,
        ),
        backtest=RuntimeBacktestSettings(
            starting_cash=settings.backtest.starting_cash,
            fee_bps=settings.backtest.fee_bps,
            trade_quantity=settings.backtest.trade_quantity,
        ),
        strategy=strategy,
        portfolio_risk=(
            RuntimePortfolioRiskSettings(
                max_daily_drawdown_pct=settings.portfolio_risk.max_daily_drawdown_pct,
                sl_pct=settings.portfolio_risk.sl_pct,
                tp_pct=settings.portfolio_risk.tp_pct,
            )
            if settings.portfolio_risk is not None
            else None
        ),
    )


def _require_key(payload: dict[str, Any], key: str, path: str) -> Any:
    if key not in payload:
        raise SettingsValidationError(f"Missing required key: '{path}'.")
    return payload[key]


def _as_dict(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SettingsValidationError(f"Invalid type for '{path}': expected mapping.")
    return value


def _as_optional_dict(value: Any, path: str) -> dict[str, Any] | None:
    if value is None:
        return None
    return _as_dict(value, path)


def _as_non_empty_str(value: Any, path: str) -> str:
    if not isinstance(value, str):
        raise SettingsValidationError(f"Invalid type for '{path}': expected string.")
    normalized = value.strip()
    if not normalized:
        raise SettingsValidationError(f"Invalid value for '{path}': must be a non-empty string.")
    return normalized


def _as_mode(value: Any, path: str) -> AppMode:
    parsed = _as_non_empty_str(value, path)
    try:
        return AppMode(parsed)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in AppMode)
        raise SettingsValidationError(
            f"Invalid value for '{path}': expected one of [{allowed}]."
        ) from exc


def _as_execution_broker(value: Any, path: str) -> str:
    parsed = _as_non_empty_str(value, path).lower()
    allowed_brokers = ("paper", "kis")
    if parsed not in allowed_brokers:
        allowed = ", ".join(allowed_brokers)
        raise SettingsValidationError(f"Invalid value for '{path}': expected one of [{allowed}].")
    return parsed


def _as_symbols(value: Any, path: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise SettingsValidationError(f"Invalid type for '{path}': expected list of strings.")

    normalized_symbols: list[str] = []
    for idx, item in enumerate(value):
        item_path = f"{path}[{idx}]"
        normalized = _as_non_empty_str(item, item_path).upper()
        normalized_symbols.append(normalized)

    if not normalized_symbols:
        raise SettingsValidationError(
            f"Invalid value for '{path}': at least one symbol is required."
        )

    return tuple(normalized_symbols)


def _as_non_empty_str_list(value: Any, path: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise SettingsValidationError(f"Invalid type for '{path}': expected list of strings.")

    normalized_values: list[str] = []
    for idx, item in enumerate(value):
        item_path = f"{path}[{idx}]"
        normalized_values.append(_as_non_empty_str(item, item_path))

    if not normalized_values:
        raise SettingsValidationError(f"Invalid value for '{path}': at least one item is required.")

    return tuple(normalized_values)


def _parse_strategy_settings(section: dict[str, Any] | None) -> StrategySettings | None:
    if section is None:
        return None
    strategy_type = _as_non_empty_str(section.get("type", "pattern_signal"), "strategy.type")
    if strategy_type != "pattern_signal":
        raise SettingsValidationError("Invalid value for 'strategy.type': expected pattern_signal.")
    profile_id = _as_optional_non_empty_str(section.get("profile_id"), "strategy.profile_id")
    pattern_set_id = _as_optional_non_empty_str(
        section.get("pattern_set_id"),
        "strategy.pattern_set_id",
    )
    label_to_side = _as_optional_label_to_side(section.get("label_to_side"))
    trade_quantity = _as_optional_decimal(
        section.get("trade_quantity"),
        "strategy.trade_quantity",
        minimum=Decimal("0"),
    )
    threshold_overrides = _as_optional_threshold_overrides(section.get("threshold_overrides"))
    return StrategySettings(
        type=strategy_type,
        profile_id=profile_id,
        pattern_set_id=pattern_set_id,
        label_to_side=label_to_side,
        trade_quantity=trade_quantity,
        threshold_overrides=threshold_overrides,
    )


def _as_optional_non_empty_str(value: Any, path: str) -> str | None:
    if value is None:
        return None
    return _as_non_empty_str(value, path)


def _as_optional_label_to_side(value: Any) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise SettingsValidationError(
            "Invalid type for 'strategy.label_to_side': expected mapping."
        )
    parsed: dict[str, str] = {}
    for label, side in value.items():
        normalized_label = _as_non_empty_str(label, "strategy.label_to_side key")
        normalized_side = _as_non_empty_str(side, f"strategy.label_to_side.{normalized_label}")
        if normalized_side not in {"buy", "sell", "hold"}:
            raise SettingsValidationError(
                "Invalid value for 'strategy.label_to_side': expected buy, sell, or hold."
            )
        parsed[normalized_label] = normalized_side
    return parsed


def _as_optional_threshold_overrides(value: Any) -> dict[str, float] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise SettingsValidationError(
            "Invalid type for 'strategy.threshold_overrides': expected mapping."
        )
    parsed: dict[str, float] = {}
    for label, threshold in value.items():
        normalized_label = _as_non_empty_str(label, "strategy.threshold_overrides key")
        try:
            parsed_threshold = float(threshold)
        except (TypeError, ValueError) as exc:
            raise SettingsValidationError(
                "Invalid type for 'strategy.threshold_overrides': expected numeric values."
            ) from exc
        if parsed_threshold < 0 or parsed_threshold > 1:
            raise SettingsValidationError(
                "Invalid value for 'strategy.threshold_overrides': expected values between 0 and 1."
            )
        parsed[normalized_label] = parsed_threshold
    return parsed


def _as_decimal(
    value: Any,
    path: str,
    minimum: Decimal | None = None,
    maximum: Decimal | None = None,
) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise SettingsValidationError(
            f"Invalid type for '{path}': expected decimal-compatible value."
        ) from exc

    if minimum is not None and number <= minimum:
        raise SettingsValidationError(
            f"Invalid value for '{path}': must be greater than {minimum}."
        )

    if maximum is not None and number > maximum:
        raise SettingsValidationError(
            f"Invalid value for '{path}': must be less than or equal to {maximum}."
        )

    return number


def _as_optional_decimal(
    value: Any,
    path: str,
    minimum: Decimal | None = None,
    maximum: Decimal | None = None,
) -> Decimal | None:
    if value is None:
        return None
    return _as_decimal(value, path, minimum=minimum, maximum=maximum)


def _as_optional_int(value: Any, path: str, minimum: int | None = None) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise SettingsValidationError(f"Invalid type for '{path}': expected integer.")
    if minimum is not None and value < minimum:
        raise SettingsValidationError(
            f"Invalid value for '{path}': must be greater than or equal to {minimum}."
        )
    return value
