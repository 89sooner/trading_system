from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def load_runtime_env(path: str | Path | None = None) -> bool:
    """Load runtime environment variables from a local dotenv file.

    Existing process environment variables keep priority over values from the
    dotenv file so production secret injection is not accidentally overwritten.
    """
    configured_path = path or os.getenv("TRADING_SYSTEM_ENV_FILE")
    if configured_path:
        return load_dotenv(Path(configured_path), override=False)

    default_path = Path.cwd() / ".env"
    if default_path.exists():
        return load_dotenv(default_path, override=False)
    return load_dotenv(override=False)
