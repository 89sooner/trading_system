from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol


class EquityWriterProtocol(Protocol):
    @property
    def session_id(self) -> str: ...

    def append(self, timestamp: str, equity: str, cash: str, positions_value: str) -> None: ...

    def read_recent(self, limit: int = 300) -> list[dict]: ...


class HistoricalEquityReaderProtocol(Protocol):
    def read_session(self, session_id: str, limit: int = 300) -> list[dict]: ...


class FileEquityWriter:
    def __init__(self, base_dir: Path | str, session_id: str) -> None:
        self._path = Path(base_dir) / f"{session_id}.jsonl"
        os.makedirs(Path(base_dir), exist_ok=True)

    @property
    def session_id(self) -> str:
        return self._path.stem

    def append(self, timestamp: str, equity: str, cash: str, positions_value: str) -> None:
        line = json.dumps({
            "timestamp": timestamp,
            "equity": equity,
            "cash": cash,
            "positions_value": positions_value,
        })
        with open(self._path, "a") as f:
            f.write(line + "\n")

    def read_recent(self, limit: int = 300) -> list[dict]:
        if not self._path.exists():
            return []
        with open(self._path) as f:
            lines = f.readlines()
        recent = lines[-limit:] if len(lines) > limit else lines
        result = []
        for line in recent:
            stripped = line.strip()
            if stripped:
                try:
                    result.append(json.loads(stripped))
                except json.JSONDecodeError:
                    continue
        return result


# Backwards-compatible alias — existing imports of EquityWriter keep working.
EquityWriter = FileEquityWriter


class FileHistoricalEquityReader:
    def __init__(self, base_dir: Path | str) -> None:
        self._base_dir = Path(base_dir)

    def read_session(self, session_id: str, limit: int = 300) -> list[dict]:
        return FileEquityWriter(self._base_dir, session_id).read_recent(limit)


def create_historical_equity_reader() -> HistoricalEquityReaderProtocol:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        from trading_system.app.supabase_equity_writer import SupabaseHistoricalEquityReader

        return SupabaseHistoricalEquityReader(database_url)
    equity_dir = Path(os.getenv("TRADING_SYSTEM_EQUITY_DIR", "data/equity"))
    return FileHistoricalEquityReader(equity_dir)
