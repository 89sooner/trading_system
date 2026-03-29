"""Shared test fixtures."""

import os
import tempfile

import pytest


@pytest.fixture(autouse=True)
def _bypass_api_key_auth():
    """Disable API key security middleware for all tests."""
    empty_keys = os.path.join(tempfile.gettempdir(), "test_empty_api_keys.json")
    if not os.path.exists(empty_keys):
        with open(empty_keys, "w") as f:
            f.write("[]")
    old = os.environ.get("TRADING_SYSTEM_API_KEYS_PATH")
    os.environ["TRADING_SYSTEM_API_KEYS_PATH"] = empty_keys
    yield
    if old is None:
        os.environ.pop("TRADING_SYSTEM_API_KEYS_PATH", None)
    else:
        os.environ["TRADING_SYSTEM_API_KEYS_PATH"] = old
