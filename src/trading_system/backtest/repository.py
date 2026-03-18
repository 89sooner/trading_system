from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from trading_system.backtest.dto import BacktestRunDTO


class BacktestRunRepository(Protocol):
    def save(self, run: BacktestRunDTO) -> None:
        ...

    def get(self, run_id: str) -> BacktestRunDTO | None:
        ...

    def clear(self) -> None:
        ...


@dataclass(slots=True)
class InMemoryBacktestRunRepository(BacktestRunRepository):
    _runs: dict[str, BacktestRunDTO] = field(default_factory=dict)

    def save(self, run: BacktestRunDTO) -> None:
        self._runs[run.run_id] = run

    def get(self, run_id: str) -> BacktestRunDTO | None:
        return self._runs.get(run_id)

    def clear(self) -> None:
        self._runs.clear()
