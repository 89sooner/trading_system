from __future__ import annotations

from trading_system.app.live_runtime_events import (
    FileLiveRuntimeEventRepository,
    LiveRuntimeEventFilter,
    LiveRuntimeEventRecord,
    runtime_event_from_log,
    should_archive_runtime_event,
)
from trading_system.core.ops import EventRecord


def _record(**kwargs) -> LiveRuntimeEventRecord:
    defaults = {
        "record_id": "event-1",
        "session_id": "session-1",
        "event": "system.error",
        "severity": "ERROR",
        "correlation_id": "cid-1",
        "timestamp": "2026-04-19T00:00:00Z",
        "payload": {"reason": "boom"},
    }
    defaults.update(kwargs)
    return LiveRuntimeEventRecord(**defaults)


def test_file_live_runtime_event_repository_filters_by_session(tmp_path) -> None:
    repo = FileLiveRuntimeEventRepository(tmp_path)
    repo.append(_record(record_id="event-1", session_id="session-1"))
    repo.append(_record(record_id="event-2", session_id="session-2"))

    records = repo.list(LiveRuntimeEventFilter(session_id="session-1"))

    assert [record.record_id for record in records] == ["event-1"]


def test_should_archive_runtime_event_uses_severity_and_prefix() -> None:
    warning = EventRecord(
        event="data.stale",
        severity="WARNING",
        correlation_id="cid-1",
        timestamp="2026-04-19T00:00:00Z",
        payload={},
    )
    reconciliation = EventRecord(
        event="portfolio.reconciliation.skipped",
        severity="INFO",
        correlation_id="cid-2",
        timestamp="2026-04-19T00:00:01Z",
        payload={},
    )
    heartbeat = EventRecord(
        event="system.heartbeat",
        severity="INFO",
        correlation_id="cid-3",
        timestamp="2026-04-19T00:00:02Z",
        payload={},
    )

    assert should_archive_runtime_event(warning) is True
    assert should_archive_runtime_event(reconciliation) is True
    assert should_archive_runtime_event(heartbeat) is False


def test_runtime_event_from_log_preserves_payload_and_session() -> None:
    record = EventRecord(
        event="system.error",
        severity="ERROR",
        correlation_id="cid-1",
        timestamp="2026-04-19T00:00:00Z",
        payload={"reason": "boom"},
    )

    archived = runtime_event_from_log(session_id="session-1", record=record)

    assert archived.session_id == "session-1"
    assert archived.event == "system.error"
    assert archived.payload == {"reason": "boom"}
