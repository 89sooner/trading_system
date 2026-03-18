from __future__ import annotations

from datetime import timezone
from enum import Enum

try:
    from enum import StrEnum as _StrEnum
except ImportError:

    class _StrEnum(str, Enum):
        """Python 3.10-compatible fallback for enum.StrEnum."""


try:
    from datetime import UTC as _UTC
except ImportError:
    _UTC = timezone.utc


StrEnum = _StrEnum
UTC = _UTC

__all__ = ["StrEnum", "UTC"]
