from datetime import datetime, timezone

from trading_system.core.compat import UTC, StrEnum


class _DemoMode(StrEnum):
    PAPER = "paper"


def test_str_enum_is_str_compatible() -> None:
    assert isinstance(_DemoMode.PAPER, str)
    assert _DemoMode("paper") == _DemoMode.PAPER


def test_utc_alias_matches_standard_utc_timezone() -> None:
    assert datetime(2024, 1, 1, tzinfo=UTC).utcoffset() == timezone.utc.utcoffset(None)
