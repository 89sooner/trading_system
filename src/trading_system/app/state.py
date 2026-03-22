from trading_system.core.compat import StrEnum


class AppRunnerState(StrEnum):
    INIT = "init"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
