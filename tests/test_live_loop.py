from unittest.mock import MagicMock

from trading_system.app.loop import LiveTradingLoop
from trading_system.app.state import AppRunnerState
from trading_system.execution.step import TradingContext


class MockExceptionLoop(LiveTradingLoop):
    def _run_tick(self, context: TradingContext) -> None:
        # Simulate network or API error
        raise ConnectionError("API disconnected")


def test_live_loop_catches_exceptions_and_pauses(monkeypatch):
    # Setup mock services
    mock_services = MagicMock()
    mock_services.logger = MagicMock()
    mock_services.portfolio = MagicMock()
    mock_services.risk_limits = MagicMock()
    mock_services.broker_simulator = MagicMock()

    loop = MockExceptionLoop(services=mock_services, poll_interval=1, heartbeat_interval=1)
    
    import time
    def mock_sleep(_):
        assert loop.state == AppRunnerState.PAUSED
        loop.state = AppRunnerState.STOPPED
    monkeypatch.setattr(time, "sleep", mock_sleep)
    
    assert loop.state == AppRunnerState.INIT
    
    # Run loop
    loop.run()
    
    # Assert state transitioned to PAUSED instead of crashing
    # Already checked in mock_sleep, but we can verify the mock was called by checking STOPPED
    assert loop.state == AppRunnerState.STOPPED
    
    # Assert logger emitted the error
    from unittest.mock import ANY
    mock_services.logger.emit.assert_any_call(
        "system.error",
        severity=40,
        payload={
            "reason": "unhandled_exception",
            "error": "API disconnected",
            "traceback": ANY
        }
    )

def test_live_loop_keyboard_interrupt():
    class MockInterruptLoop(LiveTradingLoop):
        def _check_heartbeat(self) -> None:
            raise KeyboardInterrupt()

    mock_services = MagicMock()
    mock_services.logger = MagicMock()

    loop = MockInterruptLoop(services=mock_services, poll_interval=1, heartbeat_interval=1)
    loop.run()
    
    assert loop.state == AppRunnerState.STOPPED
    mock_services.logger.emit.assert_any_call(
        "system.shutdown",
        severity=20,
        payload={"reason": "keyboard_interrupt"}
    )
