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
    label: str
    key: str
    created_at: str
    disabled: bool = False
    last_used_at: str | None = None


class ApiKeyRepository:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def list(self) -> list[ApiKeyRecord]:
        with self._lock:
            return self._load()

    def create(self, label: str) -> ApiKeyRecord:
        record = ApiKeyRecord(
            key_id=str(uuid4()),
            label=label,
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
            return any(r.key == key and not r.disabled for r in self._load())

    def set_disabled(self, key_id: str, disabled: bool) -> bool:
        with self._lock:
            records = self._load()
            updated = False
            next_records: list[ApiKeyRecord] = []
            for record in records:
                if record.key_id == key_id:
                    next_records.append(
                        ApiKeyRecord(
                            key_id=record.key_id,
                            label=record.label,
                            key=record.key,
                            created_at=record.created_at,
                            disabled=disabled,
                            last_used_at=record.last_used_at,
                        )
                    )
                    updated = True
                else:
                    next_records.append(record)
            if updated:
                self._save(next_records)
            return updated

    def record_use(self, key: str) -> bool:
        with self._lock:
            records = self._load()
            used_at = datetime.now(timezone.utc).isoformat()
            matched = False
            next_records: list[ApiKeyRecord] = []
            for record in records:
                if record.key == key and not record.disabled:
                    next_records.append(
                        ApiKeyRecord(
                            key_id=record.key_id,
                            label=record.label,
                            key=record.key,
                            created_at=record.created_at,
                            disabled=record.disabled,
                            last_used_at=used_at,
                        )
                    )
                    matched = True
                else:
                    next_records.append(record)
            if matched:
                self._save(next_records)
            return matched

    def has_any_keys(self) -> bool:
        with self._lock:
            return bool(self._load())

    def _load(self) -> list[ApiKeyRecord]:
        if not self._path.exists():
            return []
        raw = json.loads(self._path.read_text("utf-8"))
        records: list[ApiKeyRecord] = []
        for item in raw:
            label = item.get("label") or item.get("name") or ""
            records.append(
                ApiKeyRecord(
                    key_id=item["key_id"],
                    label=label,
                    key=item["key"],
                    created_at=item["created_at"],
                    disabled=bool(item.get("disabled", False)),
                    last_used_at=item.get("last_used_at"),
                )
            )
        return records

    def _save(self, records: list[ApiKeyRecord]) -> None:
        self._path.write_text(
            json.dumps([asdict(r) for r in records], indent=2),
            encoding="utf-8",
        )
