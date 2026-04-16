from types import SimpleNamespace

from trading_system.api.errors import RequestValidationError
from trading_system.api.routes.backtest import (
    _RUN_REPOSITORY,
    create_backtest_run,
    get_backtest_run,
)
from trading_system.api.routes.patterns import list_pattern_sets, save_pattern_set, train_patterns
from trading_system.api.routes.strategies import create_strategy_profile, list_strategy_profiles
from trading_system.api.schemas import (
    BacktestRunRequestDTO,
    PatternSetSaveRequestDTO,
    PatternTrainRequestDTO,
    StrategyProfileCreateDTO,
)


def test_train_save_strategy_and_run_backtest_flow(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TRADING_SYSTEM_PATTERN_DIR", str(tmp_path / "patterns"))
    monkeypatch.setenv("TRADING_SYSTEM_STRATEGY_DIR", str(tmp_path / "strategies"))

    trained = train_patterns(
        PatternTrainRequestDTO.model_validate(
            {
                "name": "Mock Window",
                "symbol": "BTCUSDT",
                "default_threshold": 0.99,
                "examples": [
                    {
                        "label": "mock_window",
                        "bars": _bars([100, 101, 103, 102]),
                    }
                ],
            }
        )
    )

    saved = save_pattern_set(PatternSetSaveRequestDTO.model_validate(trained.model_dump()))
    profile = create_strategy_profile(
        StrategyProfileCreateDTO.model_validate(
            {
                "strategy_id": "mock-profile",
                "name": "Mock Profile",
                "strategy": {
                    "type": "pattern_signal",
                    "pattern_set_id": saved.pattern_set_id,
                    "label_to_side": {"mock_window": "buy"},
                    "trade_quantity": "0.2",
                    "threshold_overrides": {"mock_window": 0.99},
                },
            }
        )
    )

    assert len(list_pattern_sets()) == 1
    assert len(list_strategy_profiles()) == 1
    assert profile.strategy.pattern_set_id == saved.pattern_set_id

    _RUN_REPOSITORY.clear()
    fake_request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    created = create_backtest_run(
        BacktestRunRequestDTO.model_validate(
            {
                "mode": "backtest",
                "symbols": ["BTCUSDT"],
                "provider": "mock",
                "broker": "paper",
                "live_execution": "preflight",
                "risk": {
                    "max_position": "1",
                    "max_notional": "100000",
                    "max_order_size": "0.25",
                },
                "backtest": {
                    "starting_cash": "10000",
                    "fee_bps": "5",
                    "trade_quantity": "0.1",
                },
                "strategy": {
                    "type": "pattern_signal",
                    "profile_id": "mock-profile",
                },
            }
        ),
        request=fake_request,
    )

    detail = get_backtest_run(created.run_id)

    assert detail.result is not None
    assert detail.result.signals
    assert detail.result.signals[0].event == "strategy.signal"
    assert detail.result.signals[0].payload["reason"].startswith("mock_window:")


def test_pattern_training_validation_raises_request_validation_error() -> None:
    try:
        train_patterns(
            PatternTrainRequestDTO.model_validate(
                {
                    "name": "Broken",
                    "symbol": "BTCUSDT",
                    "default_threshold": 0.8,
                    "examples": [
                        {
                            "label": "bad",
                            "bars": [
                                {
                                    "timestamp": "not-a-timestamp",
                                    "open": "100",
                                    "high": "100",
                                    "low": "100",
                                    "close": "100",
                                    "volume": "1",
                                },
                                {
                                    "timestamp": "2024-01-01T00:01:00Z",
                                    "open": "100",
                                    "high": "100",
                                    "low": "100",
                                    "close": "100",
                                    "volume": "1",
                                },
                            ],
                        }
                    ],
                }
            )
        )
    except RequestValidationError as exc:
        assert exc.error_code == "invalid_pattern_examples"
    else:
        raise AssertionError("Expected RequestValidationError for invalid pattern timestamps.")


def _bars(closes: list[int]) -> list[dict[str, str]]:
    rows = []
    for index, close in enumerate(closes):
        rows.append(
            {
                "timestamp": f"2024-01-01T00:0{index}:00Z",
                "open": str(close),
                "high": str(close),
                "low": str(close),
                "close": str(close),
                "volume": "1",
            }
        )
    return rows
