from pathlib import Path


def test_runtime_modules_do_not_import_datetime_utc_directly() -> None:
    src_root = Path("src/trading_system")
    violations: list[str] = []

    for path in src_root.rglob("*.py"):
        if path.as_posix().endswith("core/compat.py"):
            continue
        text = path.read_text(encoding="utf-8")
        if "from datetime import UTC" in text:
            violations.append(str(path))

    assert not violations, (
        "Runtime modules must use trading_system.core.compat.UTC for Python 3.10 compatibility: "
        + ", ".join(sorted(violations))
    )
