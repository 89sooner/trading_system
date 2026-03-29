from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from trading_system.core.compat import StrEnum


class AppRunnerState(StrEnum):
    INIT = "init"
    RUNNING = "running"
    PAUSED = "paused"
    EMERGENCY = "emergency"
    STOPPED = "stopped"


@dataclass(slots=True)
class LiveRuntimeState:
    state: AppRunnerState = AppRunnerState.INIT
    started_at: datetime | None = None
    last_heartbeat: datetime | None = None
    last_marks: dict[str, Decimal] = field(default_factory=dict)
    last_reconciliation_at: datetime | None = None
    last_reconciliation_status: str | None = None
