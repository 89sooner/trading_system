from __future__ import annotations

import json
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4


@dataclass(slots=True, frozen=True)
class ApiKeyRecord:
    key_id: str
    name: str
    key: str
    created_at: str


class ApiKeyRepository:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def list(self) -> list[ApiKeyRecord]:
        with self._lock:
            return self._load()

    def create(self, name: str) -> ApiKeyRecord:
        record = ApiKeyRecord(
            key_id=str(uuid4()),
            name=name,
            key=secrets.token_hex(24),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            records = self._load()
            records.append(record)
            self._save(records)
        return record

    def delete(self, key_id: str) -> bool:
        with self._lock:
            records = self._load()
            filtered = [r for r in records if r.key_id != key_id]
            if len(filtered) == len(records):
                return False
            self._save(filtered)
        return True

    def is_valid_key(self, key: str) -> bool:
        with self._lock:
            return any(r.key == key for r in self._load())

    def has_any_keys(self) -> bool:
        with self._lock:
            return bool(self._load())

    def _load(self) -> list[ApiKeyRecord]:
        if not self._path.exists():
            return []
        raw = json.loads(self._path.read_text("utf-8"))
        return [ApiKeyRecord(**item) for item in raw]

    def _save(self, records: list[ApiKeyRecord]) -> None:
        self._path.write_text(
            json.dumps([asdict(r) for r in records], indent=2),
            encoding="utf-8",
        )
