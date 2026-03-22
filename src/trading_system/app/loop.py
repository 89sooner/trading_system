import os
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from trading_system.app.state import AppRunnerState
from trading_system.core.compat import UTC
from trading_system.execution.step import TradingContext, execute_trading_step

if TYPE_CHECKING:
    from trading_system.app.services import AppServices


def _resolve_env_int(key: str, default: int) -> int:
    val = os.getenv(key, str(default))
    try:
        parsed = int(val)
        return parsed if parsed > 0 else default
    except ValueError:
        return default


@dataclass(slots=True)
class LiveTradingLoop:
    services: "AppServices"
    poll_interval: int = field(
        default_factory=lambda: _resolve_env_int("TRADING_SYSTEM_LIVE_POLL_INTERVAL", 10)
    )
    heartbeat_interval: int = field(
        default_factory=lambda: _resolve_env_int("TRADING_SYSTEM_HEARTBEAT_INTERVAL", 60)
    )
    state: AppRunnerState = field(default=AppRunnerState.INIT, init=False)
    _last_heartbeat: datetime | None = field(default=None, init=False)
    _last_processed_timestamps: dict[str, datetime] = field(default_factory=dict, init=False)
    _started_at: datetime | None = field(default=None, init=False)

    def run(self) -> None:
        self._started_at = datetime.now(UTC)
        self.state = AppRunnerState.RUNNING
        self.services.logger.emit("system.live_loop.start", severity=20, payload={
            "poll_interval": self.poll_interval,
            "heartbeat_interval": self.heartbeat_interval,
            "provider": self.services.provider,
            "broker": self.services.broker,
        })
        
        context = TradingContext(
            portfolio=self.services.portfolio,
            risk_limits=self.services.risk_limits,
            broker=self.services.broker_simulator,
            logger=self.services.logger,
        )

        while self.state != AppRunnerState.STOPPED:
            try:
                if self.state == AppRunnerState.RUNNING:
                    self._run_tick(context)
                    
                self._check_heartbeat()
                
                # If a hook stops the loop, break cleanly
                if self.state == AppRunnerState.STOPPED:
                    break
                    
                time.sleep(self.poll_interval)
                
            except KeyboardInterrupt:
                self.state = AppRunnerState.STOPPED
                self.services.logger.emit(
                    "system.shutdown",
                    severity=20,
                    payload={"reason": "keyboard_interrupt"}
                )
                
            except Exception as exc:
                if self.state == AppRunnerState.RUNNING:
                    self.state = AppRunnerState.PAUSED
                    self.services.logger.emit(
                        "system.error",
                        severity=40,
                        payload={
                            "reason": "unhandled_exception",
                            "error": str(exc),
                            "traceback": traceback.format_exc(),
                        }
                    )
                time.sleep(self.poll_interval)

    def _check_heartbeat(self) -> None:
        now = datetime.now(UTC)
        if (
            self._last_heartbeat is None
            or (now - self._last_heartbeat).total_seconds() >= self.heartbeat_interval
        ):
            self.services.logger.emit(
                "system.heartbeat", 
                severity=20, 
                payload={"state": self.state.value}
            )
            self._last_heartbeat = now

    def _run_tick(self, context: TradingContext) -> None:
        processed_any = False
        for symbol in self.services.symbols:
            bars = list(self.services.data_provider.load_bars(symbol))
            last_ts = self._last_processed_timestamps.get(symbol)

            for bar in bars:
                if last_ts is not None and bar.timestamp <= last_ts:
                    continue

                execute_trading_step(bar=bar, strategy=self.services.strategy, context=context)
                self._last_processed_timestamps[symbol] = bar.timestamp
                last_ts = bar.timestamp
                processed_any = True

        if processed_any and self.services.portfolio_repository is not None:
            self.services.portfolio_repository.save(self.services.portfolio)
