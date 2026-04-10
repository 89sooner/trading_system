from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from trading_system.backtest.dto import BacktestRunDTO


class BacktestRunRepository(Protocol):
    def save(self, run: BacktestRunDTO) -> None:
        ...

    def get(self, run_id: str) -> BacktestRunDTO | None:
        ...

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        mode: str | None = None,
    ) -> tuple[list[BacktestRunDTO], int]:
        ...

    def delete(self, run_id: str) -> bool:
        ...

    def clear(self) -> None:
        ...


@dataclass(slots=True)
class InMemoryBacktestRunRepository:
    _runs: dict[str, BacktestRunDTO] = field(default_factory=dict)

    def save(self, run: BacktestRunDTO) -> None:
        self._runs[run.run_id] = run

    def get(self, run_id: str) -> BacktestRunDTO | None:
        return self._runs.get(run_id)

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        mode: str | None = None,
    ) -> tuple[list[BacktestRunDTO], int]:
        runs = list(self._runs.values())
        if status is not None:
            runs = [r for r in runs if r.status == status]
        if mode is not None:
            runs = [r for r in runs if r.mode == mode]
        runs = sorted(runs, key=lambda r: r.started_at, reverse=True)
        total = len(runs)
        start = (page - 1) * page_size
        return runs[start : start + page_size], total

    def delete(self, run_id: str) -> bool:
        if run_id not in self._runs:
            return False
        del self._runs[run_id]
        return True

    def clear(self) -> None:
        self._runs.clear()
