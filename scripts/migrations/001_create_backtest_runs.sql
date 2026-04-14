CREATE TABLE IF NOT EXISTS backtest_runs (
    run_id        TEXT PRIMARY KEY,
    status        TEXT NOT NULL,
    started_at    TIMESTAMPTZ,
    finished_at   TIMESTAMPTZ,
    input_symbols TEXT[] NOT NULL DEFAULT '{}',
    mode          TEXT NOT NULL DEFAULT 'backtest',
    result        JSONB,
    error         TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE backtest_runs ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')
       AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        EXECUTE 'DROP POLICY IF EXISTS backtest_runs_deny_api_roles ON backtest_runs';
        EXECUTE '
            CREATE POLICY backtest_runs_deny_api_roles
            ON backtest_runs
            FOR ALL
            TO anon, authenticated
            USING (false)
            WITH CHECK (false)
        ';
    END IF;
END $$;
