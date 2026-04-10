"""Unit tests for EquityWriter."""
from __future__ import annotations

from trading_system.app.equity_writer import EquityWriter


def test_append_and_read_recent_roundtrip(tmp_path):
    writer = EquityWriter(tmp_path, "session-1")
    writer.append(
        timestamp="2024-01-01T00:00:00Z",
        equity="10500",
        cash="5000",
        positions_value="5500",
    )
    points = writer.read_recent()
    assert len(points) == 1
    assert points[0]["equity"] == "10500"
    assert points[0]["cash"] == "5000"
    assert points[0]["positions_value"] == "5500"
    assert points[0]["timestamp"] == "2024-01-01T00:00:00Z"


def test_read_recent_empty_file(tmp_path):
    writer = EquityWriter(tmp_path, "session-empty")
    result = writer.read_recent()
    assert result == []


def test_read_recent_missing_file(tmp_path):
    writer = EquityWriter(tmp_path, "session-missing")
    result = writer.read_recent()
    assert result == []


def test_read_recent_limit(tmp_path):
    writer = EquityWriter(tmp_path, "session-limit")
    for i in range(10):
        writer.append(
            timestamp=f"2024-01-01T00:0{i}:00Z",
            equity=str(10000 + i),
            cash="5000",
            positions_value=str(5000 + i),
        )

    recent = writer.read_recent(limit=5)
    assert len(recent) == 5
    # Should be the last 5 appended
    assert recent[-1]["equity"] == "10009"
    assert recent[0]["equity"] == "10005"


def test_append_multiple_sessions_independent(tmp_path):
    w1 = EquityWriter(tmp_path, "session-a")
    w2 = EquityWriter(tmp_path, "session-b")

    w1.append(timestamp="2024-01-01T00:00:00Z", equity="1000", cash="500", positions_value="500")
    w2.append(timestamp="2024-01-01T00:00:00Z", equity="2000", cash="1000", positions_value="1000")

    assert w1.read_recent()[0]["equity"] == "1000"
    assert w2.read_recent()[0]["equity"] == "2000"


def test_session_id_property(tmp_path):
    writer = EquityWriter(tmp_path, "my-session")
    assert writer.session_id == "my-session"
