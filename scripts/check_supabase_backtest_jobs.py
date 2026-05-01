from __future__ import annotations

import os
import sys
from dataclasses import dataclass

import psycopg

EXPECTED_COLUMNS = {
    "run_id",
    "status",
    "payload",
    "created_at",
    "available_at",
    "attempt_count",
    "max_attempts",
    "worker_id",
    "lease_expires_at",
    "last_heartbeat_at",
    "progress",
    "cancel_requested",
    "error",
}

EXPECTED_INDEXES = {
    "idx_backtest_jobs_claim",
    "idx_backtest_jobs_worker",
}


@dataclass(slots=True, frozen=True)
class BacktestJobsSchemaCheck:
    columns: set[str]
    indexes: set[str]
    rls_enabled: bool
    policies: set[str]


def _load_schema(database_url: str) -> BacktestJobsSchemaCheck:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'backtest_jobs'
                """
            )
            columns = {row[0] for row in cursor.fetchall()}

            cursor.execute(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public' AND tablename = 'backtest_jobs'
                """
            )
            indexes = {row[0] for row in cursor.fetchall()}

            cursor.execute(
                """
                SELECT relrowsecurity
                FROM pg_class
                WHERE oid = 'public.backtest_jobs'::regclass
                """
            )
            row = cursor.fetchone()
            rls_enabled = bool(row[0]) if row is not None else False

            cursor.execute(
                """
                SELECT policyname
                FROM pg_policies
                WHERE schemaname = 'public' AND tablename = 'backtest_jobs'
                """
            )
            policies = {row[0] for row in cursor.fetchall()}

    return BacktestJobsSchemaCheck(
        columns=columns,
        indexes=indexes,
        rls_enabled=rls_enabled,
        policies=policies,
    )


def _validate(check: BacktestJobsSchemaCheck) -> list[str]:
    errors: list[str] = []
    missing_columns = sorted(EXPECTED_COLUMNS - check.columns)
    if missing_columns:
        errors.append(f"missing columns: {', '.join(missing_columns)}")

    missing_indexes = sorted(EXPECTED_INDEXES - check.indexes)
    if missing_indexes:
        errors.append(f"missing indexes: {', '.join(missing_indexes)}")

    if not check.rls_enabled:
        errors.append("RLS is not enabled on public.backtest_jobs")

    if "deny_backtest_jobs_client_access" not in check.policies:
        errors.append("missing deny_backtest_jobs_client_access policy")

    return errors


def main() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set; cannot check Supabase backtest_jobs schema.")

    errors = _validate(_load_schema(database_url))
    if errors:
        print("Supabase backtest_jobs schema check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        raise SystemExit(1)

    print("Supabase backtest_jobs schema check passed")


if __name__ == "__main__":
    main()
