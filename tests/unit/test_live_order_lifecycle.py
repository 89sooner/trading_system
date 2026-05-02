from trading_system.execution.live_orders import (
    FileLiveOrderRepository,
    LiveOrderFilter,
    LiveOrderStatus,
    new_live_order_record,
)


def test_file_live_order_repository_lifecycle(tmp_path):
    repo = FileLiveOrderRepository(tmp_path)
    record = new_live_order_record(
        session_id="live_1",
        symbol="005930",
        side="buy",
        requested_quantity="3",
        filled_quantity="0",
        remaining_quantity="3",
        status=LiveOrderStatus.SUBMITTED.value,
        broker_order_id="90001",
        submitted_at="2026-05-01T00:00:00+00:00",
        stale_after="2026-05-01T00:01:00+00:00",
    )

    repo.upsert(record)
    assert repo.get(record.record_id) == record
    assert repo.list_active(session_id="live_1")[0].record_id == record.record_id
    assert repo.list_stale(now="2026-05-01T00:02:00+00:00", session_id="live_1")

    cancelled = repo.mark_cancel_requested(
        record.record_id,
        requested_at="2026-05-01T00:00:30+00:00",
    )

    assert cancelled is not None
    assert cancelled.status == LiveOrderStatus.CANCEL_REQUESTED.value
    assert cancelled.cancel_requested is True

    updated = repo.update_from_broker(
        record.record_id,
        status=LiveOrderStatus.PARTIALLY_FILLED.value,
        filled_quantity="1",
        remaining_quantity="2",
        synced_at="2026-05-01T00:00:40+00:00",
    )

    assert updated is not None
    assert updated.filled_quantity == "1"
    assert updated.remaining_quantity == "2"
    records = repo.list(LiveOrderFilter(status=LiveOrderStatus.PARTIALLY_FILLED.value))
    assert records[0].record_id == record.record_id


def test_terminal_orders_are_not_active(tmp_path):
    repo = FileLiveOrderRepository(tmp_path)
    record = new_live_order_record(
        session_id="live_1",
        symbol="005930",
        side="sell",
        requested_quantity="1",
        filled_quantity="1",
        remaining_quantity="0",
        status=LiveOrderStatus.FILLED.value,
        broker_order_id="90002",
        submitted_at="2026-05-01T00:00:00+00:00",
    )
    repo.upsert(record)

    assert repo.get(record.record_id).is_terminal is True
    assert repo.list_active(session_id="live_1") == []
