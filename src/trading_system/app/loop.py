import os
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from trading_system.app.equity_writer import EquityWriterProtocol
from trading_system.app.state import AppRunnerState, LiveRuntimeState
from trading_system.core.compat import UTC
from trading_system.execution.broker import AccountBalanceSnapshot
from trading_system.execution.live_orders import LiveOrderStatus, new_live_order_record
from trading_system.execution.order_audit import append_step_order_audit_events
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
    order_poll_interval: int = field(
        default_factory=lambda: _resolve_env_int("TRADING_SYSTEM_ORDER_POLL_INTERVAL", 30)
    )
    order_stale_after_seconds: int = field(
        default_factory=lambda: _resolve_env_int("TRADING_SYSTEM_ORDER_STALE_AFTER_SECONDS", 120)
    )
    equity_writer: EquityWriterProtocol | None = field(default=None)
    audit_owner_id: str | None = field(default=None)
    runtime: LiveRuntimeState = field(default_factory=LiveRuntimeState, init=False)
    _last_processed_timestamps: dict[str, datetime] = field(default_factory=dict, init=False)
    _last_reconciliation: datetime | None = field(default=None, init=False)
    _last_order_sync: datetime | None = field(default=None, init=False)
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
            order_audit_repository=self.services.order_audit_repository,
            order_audit_scope="live_session",
            order_audit_owner_id=self.audit_owner_id,
        )

        while self.state != AppRunnerState.STOPPED:
            try:
                if self.state == AppRunnerState.RUNNING:
                    self._maybe_sync_live_orders()
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
                try:
                    time.sleep(self.poll_interval)
                except KeyboardInterrupt:
                    self.state = AppRunnerState.STOPPED
                    self.services.logger.emit(
                        "system.shutdown",
                        severity=20,
                        payload={"reason": "keyboard_interrupt"},
                    )

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
        if self._has_blocking_live_orders():
            return

        processed_any = False
        for symbol in self.services.symbols:
            bars = list(self.services.data_provider.load_bars(symbol))
            last_ts = self._last_processed_timestamps.get(symbol)

            for bar in bars:
                if last_ts is not None and bar.timestamp <= last_ts:
                    continue

                events = execute_trading_step(
                    bar=bar,
                    strategy=self.services.strategy_for(symbol),
                    context=context,
                )
                append_step_order_audit_events(
                    repository=context.order_audit_repository,
                    scope=context.order_audit_scope,
                    owner_id=context.order_audit_owner_id,
                    events=events,
                )
                self._append_live_order_lifecycle(events)
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

    def _append_live_order_lifecycle(self, events) -> None:
        repository = getattr(self.services, "live_order_repository", None)
        if repository is None or self.audit_owner_id is None:
            return
        now = datetime.now(UTC)
        stale_after = (now + timedelta(seconds=self.order_stale_after_seconds)).isoformat()
        filled = events.order_filled
        rejected = events.order_rejected
        if filled is not None:
            broker_order_id = filled.get("broker_order_id")
            requested = str(filled.get("requested_quantity", "0"))
            filled_quantity = str(filled.get("filled_quantity", "0"))
            remaining = str(max(Decimal(requested) - Decimal(filled_quantity), Decimal("0")))
            status = LiveOrderStatus.FILLED.value
            if broker_order_id is not None:
                status = LiveOrderStatus.SUBMITTED.value
                remaining = requested
                filled_quantity = "0"
            repository.upsert(
                new_live_order_record(
                    session_id=self.audit_owner_id,
                    symbol=str(filled.get("symbol")),
                    side=str(filled.get("side")),
                    requested_quantity=requested,
                    filled_quantity=filled_quantity,
                    remaining_quantity=remaining,
                    status=status,
                    broker_order_id=str(broker_order_id) if broker_order_id is not None else None,
                    submitted_at=now.isoformat(),
                    stale_after=stale_after if broker_order_id is not None else None,
                    payload=dict(filled),
                )
            )
        if rejected is not None:
            repository.upsert(
                new_live_order_record(
                    session_id=self.audit_owner_id,
                    symbol=str(rejected.get("symbol")),
                    side=str(rejected.get("side")),
                    requested_quantity=str(rejected.get("quantity", "0")),
                    filled_quantity="0",
                    remaining_quantity=str(rejected.get("quantity", "0")),
                    status=LiveOrderStatus.REJECTED.value,
                    broker_order_id=None,
                    submitted_at=now.isoformat(),
                    payload=dict(rejected),
                )
            )

    def _maybe_sync_live_orders(self) -> None:
        repository = getattr(self.services, "live_order_repository", None)
        if repository is None or self.audit_owner_id is None:
            return
        now = datetime.now(UTC)
        if (
            self._last_order_sync is not None
            and (now - self._last_order_sync).total_seconds() < self.order_poll_interval
        ):
            self._mark_stale_live_orders(now)
            return
        self._last_order_sync = now
        active_orders = repository.list_active(session_id=self.audit_owner_id)
        if not active_orders:
            return
        try:
            snapshot = self.services.broker_simulator.get_open_orders()
        except Exception as exc:
            for record in active_orders:
                repository.update_from_broker(
                    record.record_id,
                    status=record.status,
                    filled_quantity=record.filled_quantity,
                    remaining_quantity=record.remaining_quantity,
                    synced_at=now.isoformat(),
                    last_error=str(exc),
                )
            self.services.logger.emit(
                "live_order.sync_failed",
                severity=40,
                payload={"reason": "open_orders_unavailable", "error": str(exc)},
            )
            self._mark_stale_live_orders(now)
            return
        open_orders = {
            order.broker_order_id: order
            for order in (snapshot.orders if snapshot is not None else ())
        }
        for record in active_orders:
            if record.broker_order_id is None:
                continue
            order = open_orders.get(record.broker_order_id)
            if order is None:
                repository.update_from_broker(
                    record.record_id,
                    status=LiveOrderStatus.UNKNOWN.value,
                    filled_quantity=record.filled_quantity,
                    remaining_quantity=record.remaining_quantity,
                    synced_at=now.isoformat(),
                    last_error="broker_order_missing_from_open_orders",
                )
                continue
            requested = order.requested_quantity
            remaining = order.remaining_quantity
            filled = max(requested - remaining, Decimal("0"))
            status = (
                LiveOrderStatus.PARTIALLY_FILLED
                if filled > 0 and remaining > 0
                else LiveOrderStatus.OPEN
                if remaining > 0
                else LiveOrderStatus.FILLED
            )
            repository.update_from_broker(
                record.record_id,
                status=status.value,
                filled_quantity=str(filled),
                remaining_quantity=str(remaining),
                synced_at=now.isoformat(),
                broker_order_id=order.broker_order_id,
                payload={
                    "broker_order_id": order.broker_order_id,
                    "status": order.status,
                    "submitted_at": order.submitted_at,
                },
            )
        self._mark_stale_live_orders(now)

    def _mark_stale_live_orders(self, now: datetime) -> None:
        repository = getattr(self.services, "live_order_repository", None)
        if repository is None or self.audit_owner_id is None:
            return
        for record in repository.list_stale(now=now.isoformat(), session_id=self.audit_owner_id):
            if record.status == LiveOrderStatus.STALE.value:
                continue
            repository.update_from_broker(
                record.record_id,
                status=LiveOrderStatus.STALE.value,
                filled_quantity=record.filled_quantity,
                remaining_quantity=record.remaining_quantity,
                synced_at=now.isoformat(),
                last_error=record.last_error or "order_status_stale",
            )
            self.services.logger.emit(
                "live_order.stale",
                severity=40,
                payload={
                    "record_id": record.record_id,
                    "broker_order_id": record.broker_order_id,
                    "symbol": record.symbol,
                    "stale_after": record.stale_after,
                },
            )

    def _has_blocking_live_orders(self) -> bool:
        repository = getattr(self.services, "live_order_repository", None)
        if repository is None or self.audit_owner_id is None:
            return False
        active = repository.list_active(session_id=self.audit_owner_id)
        blocking = [
            record
            for record in active
            if record.status
            in {
                LiveOrderStatus.SUBMITTED.value,
                LiveOrderStatus.OPEN.value,
                LiveOrderStatus.PARTIALLY_FILLED.value,
                LiveOrderStatus.CANCEL_REQUESTED.value,
                LiveOrderStatus.STALE.value,
                LiveOrderStatus.UNKNOWN.value,
            }
        ]
        if not blocking:
            return False
        self.services.logger.emit(
            "live_order.gate_blocked",
            severity=30,
            payload={
                "reason": "active_or_stale_order",
                "order_count": len(blocking),
                "record_ids": [record.record_id for record in blocking[:10]],
            },
        )
        return True

    def _maybe_reconcile(self) -> None:
        repository = getattr(self.services, "live_order_repository", None)
        if repository is not None and self.audit_owner_id is not None:
            active = repository.list_active(session_id=self.audit_owner_id)
            if active:
                self.runtime.last_reconciliation_at = datetime.now(UTC)
                self.runtime.last_reconciliation_status = "skipped"
                self.services.logger.emit(
                    "portfolio.reconciliation.skipped",
                    severity=30,
                    payload={
                        "reason": "active_live_order",
                        "pending_order_count": len(active),
                    },
                )
                return
        now = datetime.now(UTC)
        if (
            self._last_reconciliation is not None
            and (now - self._last_reconciliation).total_seconds() < self.reconciliation_interval
        ):
            return
        try:
            open_orders = self.services.broker_simulator.get_open_orders()
        except Exception as exc:
            self._last_reconciliation = now
            self.runtime.last_reconciliation_at = now
            self.runtime.last_reconciliation_status = "skipped"
            self.services.logger.emit(
                "portfolio.reconciliation.skipped",
                severity=40,
                payload={
                    "reason": "open_orders_unavailable",
                    "error": str(exc),
                    "pending_source": "open_orders",
                },
            )
            return

        snapshot = self.services.broker_simulator.get_account_balance()
        if snapshot is None:
            self._last_reconciliation = now
            self.runtime.last_reconciliation_at = now
            self.runtime.last_reconciliation_status = "skipped"
            self.services.logger.emit(
                "portfolio.reconciliation.skipped",
                    severity=30,
                payload={"reason": "snapshot_unavailable", "pending_source": "unavailable"},
            )
            return
        pending_source = "balance_snapshot"
        if open_orders is not None:
            pending_source = "open_orders"
            snapshot = AccountBalanceSnapshot(
                cash=snapshot.cash,
                positions=snapshot.positions,
                average_costs=snapshot.average_costs,
                pending_symbols=open_orders.pending_symbols,
            )
        self.services.logger.emit(
            "portfolio.reconciliation.pending_source",
            severity=20,
            payload={
                "pending_source": pending_source,
                "pending_symbol_count": len(snapshot.pending_symbols),
            },
        )
        reconcile(
            book=self.services.portfolio,
            snapshot=snapshot,
            logger=self.services.logger,
        )
        self._last_reconciliation = now
        self.runtime.last_reconciliation_at = now
        self.runtime.last_reconciliation_status = "completed"
