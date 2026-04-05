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
