ALTER TABLE backtest_runs
    ADD COLUMN IF NOT EXISTS metadata JSONB;


CREATE TABLE IF NOT EXISTS live_runtime_sessions (
    session_id         TEXT PRIMARY KEY,
    started_at         TIMESTAMPTZ NOT NULL,
    ended_at           TIMESTAMPTZ,
    provider           TEXT NOT NULL,
    broker             TEXT NOT NULL,
    live_execution     TEXT NOT NULL,
    symbols            TEXT[] NOT NULL DEFAULT '{}',
    last_state         TEXT NOT NULL,
    last_error         TEXT,
    preflight_summary  JSONB,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_live_runtime_sessions_started_at
    ON live_runtime_sessions (started_at DESC);

ALTER TABLE live_runtime_sessions ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')
       AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        EXECUTE 'DROP POLICY IF EXISTS live_runtime_sessions_deny_api_roles ON live_runtime_sessions';
        EXECUTE '
            CREATE POLICY live_runtime_sessions_deny_api_roles
            ON live_runtime_sessions
            FOR ALL
            TO anon, authenticated
            USING (false)
            WITH CHECK (false)
        ';
    END IF;
END $$;
