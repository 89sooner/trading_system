"""Unit tests for SupabaseBacktestRunRepository using mocked psycopg3 connections."""
from __future__ import annotations

import importlib
import os
from unittest.mock import MagicMock, patch

import pytest

from trading_system.backtest.dto import BacktestRunDTO, BacktestRunMetadataDTO


def _make_run(**kwargs) -> BacktestRunDTO:
    defaults = dict(
        run_id="run-1",
        status="succeeded",
        started_at="2024-01-01T00:00:00",
        finished_at="2024-01-01T00:01:00",
        input_symbols=["BTCUSDT"],
        mode="backtest",
        metadata=None,
        result=None,
        error=None,
    )
    defaults.update(kwargs)
    return BacktestRunDTO(**defaults)


def _make_repo():
    """Return a SupabaseBacktestRunRepository with a fully-mocked psycopg3 connection."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.closed = False  # Prevent _get_conn from reconnecting

    from trading_system.backtest.supabase_repository import SupabaseBacktestRunRepository
    repo = SupabaseBacktestRunRepository("postgresql://fake/db")
    repo._conn = mock_conn  # Inject mock directly; constructor no longer connects eagerly

    return repo, mock_conn, mock_cursor


class TestSaveExecutesUpsert:
    def test_save_calls_execute_with_run_id(self):
        repo, _, mock_cursor = _make_repo()
        run = _make_run()
        repo.save(run)
        assert mock_cursor.execute.called
        sql, params = mock_cursor.execute.call_args[0]
        assert "INSERT INTO backtest_runs" in sql
        assert "ON CONFLICT" in sql
        assert params[0] == "run-1"

    def test_save_result_none_passes_null(self):
        repo, _, mock_cursor = _make_repo()
        repo.save(_make_run(result=None))
        _, params = mock_cursor.execute.call_args[0]
        assert params[7] is None

    def test_save_metadata_serializes_json(self):
        repo, _, mock_cursor = _make_repo()
        repo.save(
            _make_run(
                metadata=BacktestRunMetadataDTO(
                    provider="mock",
                    broker="paper",
                    source="frontend",
                )
            )
        )
        _, params = mock_cursor.execute.call_args[0]
        assert params[6] is not None


class TestGet:
    def test_get_returns_dto_when_row_exists(self):
        repo, _, mock_cursor = _make_repo()
        mock_cursor.fetchone.return_value = (
            "run-1", "succeeded",
            "2024-01-01T00:00:00", "2024-01-01T00:01:00",
            ["BTCUSDT"], "backtest", None, None, None,
        )
        result = repo.get("run-1")
        assert result is not None
        assert result.run_id == "run-1"
        assert result.status == "succeeded"

    def test_get_returns_none_when_no_row(self):
        repo, _, mock_cursor = _make_repo()
        mock_cursor.fetchone.return_value = None
        assert repo.get("missing") is None

    def test_get_preserves_nullable_finished_at_for_pending_run(self):
        repo, _, mock_cursor = _make_repo()
        mock_cursor.fetchone.return_value = (
            "run-1", "queued",
            "2024-01-01T00:00:00", None,
            ["BTCUSDT"], "backtest", None, None, None,
        )
        result = repo.get("run-1")
        assert result is not None
        assert result.status == "queued"
        assert result.finished_at is None

    def test_get_deserializes_metadata_when_present(self):
        repo, _, mock_cursor = _make_repo()
        mock_cursor.fetchone.return_value = (
            "run-1",
            "succeeded",
            "2024-01-01T00:00:00",
            "2024-01-01T00:01:00",
            ["BTCUSDT"],
            "backtest",
            {"provider": "mock", "broker": "paper", "source": "frontend"},
            None,
            None,
        )
        result = repo.get("run-1")
        assert result is not None
        assert result.metadata is not None
        assert result.metadata.provider == "mock"


class TestList:
    def test_list_passes_status_filter(self):
        repo, _, mock_cursor = _make_repo()
        mock_cursor.fetchone.return_value = (0,)
        mock_cursor.fetchall.return_value = []
        repo.list(page=1, page_size=10, status="succeeded")
        calls = [str(c) for c in mock_cursor.execute.call_args_list]
        assert any("succeeded" in str(c) for c in calls)

    def test_list_passes_mode_filter(self):
        repo, _, mock_cursor = _make_repo()
        mock_cursor.fetchone.return_value = (0,)
        mock_cursor.fetchall.return_value = []
        repo.list(page=1, page_size=10, mode="backtest")
        calls = [str(c) for c in mock_cursor.execute.call_args_list]
        assert any("backtest" in str(c) for c in calls)

    def test_list_returns_total_from_count(self):
        repo, _, mock_cursor = _make_repo()
        mock_cursor.fetchone.return_value = (42,)
        mock_cursor.fetchall.return_value = []
        _, total = repo.list()
        assert total == 42


class TestDelete:
    def test_delete_returns_false_when_rowcount_zero(self):
        repo, _, mock_cursor = _make_repo()
        mock_cursor.rowcount = 0
        assert repo.delete("missing") is False

    def test_delete_returns_true_when_rowcount_one(self):
        repo, _, mock_cursor = _make_repo()
        mock_cursor.rowcount = 1
        assert repo.delete("run-1") is True


class TestRebuildIndex:
    def test_rebuild_index_is_noop(self):
        repo, _, mock_cursor = _make_repo()
        # Should not raise and should not execute any SQL.
        repo.rebuild_index()
        mock_cursor.execute.assert_not_called()


class TestBacktestRouteRepositorySelection:
    def test_create_run_repository_uses_supabase_when_database_url_present(self, monkeypatch):
        from trading_system.api.routes import backtest as backtest_module

        fake_repo = MagicMock()
        monkeypatch.setenv("DATABASE_URL", "postgresql://supabase.example/db")

        with patch(
            "trading_system.backtest.supabase_repository.SupabaseBacktestRunRepository",
            return_value=fake_repo,
        ) as repo_cls:
            result = backtest_module._create_run_repository()

        repo_cls.assert_called_once_with("postgresql://supabase.example/db")
        assert result is fake_repo

    def test_create_run_repository_uses_file_repo_without_database_url(self, monkeypatch, tmp_path):
        from trading_system.api.routes import backtest as backtest_module

        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("TRADING_SYSTEM_RUNS_DIR", str(tmp_path))

        result = backtest_module._create_run_repository()

        from trading_system.backtest.file_repository import FileBacktestRunRepository

        assert isinstance(result, FileBacktestRunRepository)

    def test_module_level_repository_can_be_rebuilt_after_env_change(self, monkeypatch):
        from trading_system.api.routes import backtest as backtest_module

        monkeypatch.setenv("DATABASE_URL", "postgresql://supabase.example/db")
        fake_repo = MagicMock()

        try:
            with patch(
                "trading_system.backtest.supabase_repository.SupabaseBacktestRunRepository",
                return_value=fake_repo,
            ):
                reloaded = importlib.reload(backtest_module)
            assert reloaded._RUN_REPOSITORY is fake_repo
        finally:
            monkeypatch.delenv("DATABASE_URL", raising=False)
            importlib.reload(backtest_module)


# ---------------------------------------------------------------------------
# Integration-style test — skipped when DATABASE_URL is not set
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL") or os.environ.get("RUN_SUPABASE_INTEGRATION_TESTS") != "1",
    reason="Supabase integration test requires DATABASE_URL and RUN_SUPABASE_INTEGRATION_TESTS=1",
)
class TestIntegration:
    def test_save_and_get_roundtrip(self):
        from trading_system.backtest.supabase_repository import SupabaseBacktestRunRepository
        repo = SupabaseBacktestRunRepository(os.environ["DATABASE_URL"])
        run = _make_run(run_id="integration-test-run")
        repo.save(run)
        fetched = repo.get("integration-test-run")
        assert fetched is not None
        assert fetched.run_id == "integration-test-run"
        repo.delete("integration-test-run")
