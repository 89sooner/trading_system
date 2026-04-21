from __future__ import annotations

from trading_system.api.admin.repository import ApiKeyRepository


def test_create_and_list_roundtrip(tmp_path) -> None:
    repo = ApiKeyRepository(tmp_path / "api_keys.json")

    record = repo.create("operator-console")
    listed = repo.list()

    assert len(listed) == 1
    assert listed[0].key_id == record.key_id
    assert listed[0].label == "operator-console"
    assert listed[0].disabled is False
    assert listed[0].last_used_at is None


def test_disabled_key_is_not_valid(tmp_path) -> None:
    repo = ApiKeyRepository(tmp_path / "api_keys.json")
    record = repo.create("operator-console")

    assert repo.is_valid_key(record.key) is True
    assert repo.set_disabled(record.key_id, True) is True
    assert repo.is_valid_key(record.key) is False


def test_record_use_updates_last_used_at(tmp_path) -> None:
    repo = ApiKeyRepository(tmp_path / "api_keys.json")
    record = repo.create("operator-console")

    assert repo.record_use(record.key) is True
    refreshed = repo.list()[0]
    assert refreshed.last_used_at is not None


def test_load_legacy_name_field_as_label(tmp_path) -> None:
    path = tmp_path / "api_keys.json"
    path.write_text(
        '[{"key_id":"k1","name":"legacy-name","key":"secret","created_at":"2026-01-01T00:00:00Z"}]',
        encoding="utf-8",
    )
    repo = ApiKeyRepository(path)

    listed = repo.list()

    assert len(listed) == 1
    assert listed[0].label == "legacy-name"
