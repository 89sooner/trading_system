import os
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from trading_system.app.equity_writer import EquityWriter
from trading_system.app.state import AppRunnerState, LiveRuntimeState
from trading_system.core.compat import UTC
from trading_system.execution.reconciliation import reconcile
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
    reconciliation_interval: int = field(
        default_factory=lambda: _resolve_env_int("TRADING_SYSTEM_RECONCILIATION_INTERVAL", 300)
    )
    equity_writer: EquityWriter | None = field(default=None)
    runtime: LiveRuntimeState = field(default_factory=LiveRuntimeState, init=False)
    _last_processed_timestamps: dict[str, datetime] = field(default_factory=dict, init=False)
    _last_reconciliation: datetime | None = field(default=None, init=False)
    _last_position_snapshot: dict[str, str] = field(default_factory=dict, init=False)

    @property
    def state(self) -> AppRunnerState:
        return self.runtime.state

    @state.setter
    def state(self, value: AppRunnerState) -> None:
        self.runtime.state = value
        try:
            self.services.logger.emit(
                "sse.status",
                severity=20,
                payload={"state": value.value},
            )
        except Exception:
            pass

    @property
    def _last_heartbeat(self) -> datetime | None:
        return self.runtime.last_heartbeat

    @_last_heartbeat.setter
    def _last_heartbeat(self, value: datetime | None) -> None:
        self.runtime.last_heartbeat = value

    @property
    def _started_at(self) -> datetime | None:
        return self.runtime.started_at

    @_started_at.setter
    def _started_at(self, value: datetime | None) -> None:
        self.runtime.started_at = value

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
            portfolio_risk=self.services.portfolio_risk,
            runtime_state=self.runtime,
            marks=self.runtime.last_marks,
        )

        while self.state != AppRunnerState.STOPPED:
            try:
                if self.state == AppRunnerState.RUNNING:
                    self._maybe_reconcile()
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
                payload={"state": self.state.value},
            )
            self._last_heartbeat = now
            # Record equity snapshot
            marks = self.runtime.last_marks
            equity = self.services.portfolio.total_equity(marks)
            cash = self.services.portfolio.cash
            positions_value = equity - cash
            if self.equity_writer is not None:
                self.equity_writer.append(
                    timestamp=now.isoformat(),
                    equity=str(equity),
                    cash=str(cash),
                    positions_value=str(positions_value),
                )
            self.services.logger.emit(
                "sse.equity",
                severity=20,
                payload={
                    "timestamp": now.isoformat(),
                    "equity": str(equity),
                    "cash": str(cash),
                    "positions_value": str(positions_value),
                },
            )

    def _run_tick(self, context: TradingContext) -> None:
        processed_any = False
        for symbol in self.services.symbols:
            bars = list(self.services.data_provider.load_bars(symbol))
            last_ts = self._last_processed_timestamps.get(symbol)

            for bar in bars:
                if last_ts is not None and bar.timestamp <= last_ts:
                    continue

                execute_trading_step(
                    bar=bar,
                    strategy=self.services.strategy_for(symbol),
                    context=context,
                )
                self._last_processed_timestamps[symbol] = bar.timestamp
                last_ts = bar.timestamp
                processed_any = True

        if processed_any and self.services.portfolio_repository is not None:
            self.services.portfolio_repository.save(self.services.portfolio)

        # Emit SSE position event if positions changed
        current_snapshot = {
            symbol: str(qty)
            for symbol, qty in self.services.portfolio.positions.items()
        }
        if current_snapshot != self._last_position_snapshot:
            self._last_position_snapshot = current_snapshot
            self.services.logger.emit(
                "sse.position",
                severity=20,
                payload={"positions": current_snapshot},
            )

    def _maybe_reconcile(self) -> None:
        now = datetime.now(UTC)
        if (
            self._last_reconciliation is not None
            and (now - self._last_reconciliation).total_seconds() < self.reconciliation_interval
        ):
            return
        snapshot = self.services.broker_simulator.get_account_balance()
        if snapshot is None:
            self._last_reconciliation = now
            self.runtime.last_reconciliation_at = now
            self.runtime.last_reconciliation_status = "skipped"
            self.services.logger.emit(
                "portfolio.reconciliation.skipped",
                severity=30,
                payload={"reason": "snapshot_unavailable"},
            )
            return
        reconcile(
            book=self.services.portfolio,
            snapshot=snapshot,
            logger=self.services.logger,
        )
        self._last_reconciliation = now
        self.runtime.last_reconciliation_at = now
        self.runtime.last_reconciliation_status = "completed"
