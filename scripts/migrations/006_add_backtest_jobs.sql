CREATE TABLE IF NOT EXISTS backtest_jobs (
    run_id             TEXT PRIMARY KEY REFERENCES backtest_runs(run_id) ON DELETE CASCADE,
    status             TEXT NOT NULL,
    payload            JSONB NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL,
    available_at       TIMESTAMPTZ NOT NULL,
    attempt_count      INTEGER NOT NULL DEFAULT 0,
    max_attempts       INTEGER NOT NULL DEFAULT 3,
    worker_id          TEXT,
    lease_expires_at   TIMESTAMPTZ,
    last_heartbeat_at  TIMESTAMPTZ,
    progress           JSONB,
    cancel_requested   BOOLEAN NOT NULL DEFAULT FALSE,
    error              TEXT
);

CREATE INDEX IF NOT EXISTS idx_backtest_jobs_claim
    ON backtest_jobs (status, available_at, lease_expires_at);

CREATE INDEX IF NOT EXISTS idx_backtest_jobs_worker
    ON backtest_jobs (worker_id, lease_expires_at)
    WHERE status = 'running';

ALTER TABLE backtest_jobs ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')
       AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        EXECUTE 'DROP POLICY IF EXISTS backtest_jobs_deny_api_roles ON backtest_jobs';
        EXECUTE '
            CREATE POLICY backtest_jobs_deny_api_roles
            ON backtest_jobs
            FOR ALL
            TO anon, authenticated
            USING (false)
            WITH CHECK (false)
        ';
    END IF;
END $$;
