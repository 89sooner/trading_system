"""Shared test fixtures."""

import os
import tempfile

import pytest


@pytest.fixture(autouse=True)
def _bypass_api_key_auth():
    """Disable API key security middleware for all tests.

    Clears both the repo-based key path and the env-var-based allowed keys so
    that .env values (loaded by load_dotenv() in server.py) do not bleed
    across test cases.
    """
    empty_keys = os.path.join(tempfile.gettempdir(), "test_empty_api_keys.json")
    if not os.path.exists(empty_keys):
        with open(empty_keys, "w") as f:
            f.write("[]")

    old_path = os.environ.get("TRADING_SYSTEM_API_KEYS_PATH")
    old_allowed = os.environ.get("TRADING_SYSTEM_ALLOWED_API_KEYS")

    os.environ["TRADING_SYSTEM_API_KEYS_PATH"] = empty_keys
    os.environ["TRADING_SYSTEM_ALLOWED_API_KEYS"] = ""

    yield

    if old_path is None:
        os.environ.pop("TRADING_SYSTEM_API_KEYS_PATH", None)
    else:
        os.environ["TRADING_SYSTEM_API_KEYS_PATH"] = old_path

    if old_allowed is None:
        os.environ.pop("TRADING_SYSTEM_ALLOWED_API_KEYS", None)
    else:
        os.environ["TRADING_SYSTEM_ALLOWED_API_KEYS"] = old_allowed
