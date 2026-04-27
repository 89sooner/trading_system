CREATE TABLE IF NOT EXISTS live_runtime_events (
    record_id      TEXT PRIMARY KEY,
    session_id     TEXT NOT NULL,
    event          TEXT NOT NULL,
    severity       TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    timestamp      TIMESTAMPTZ NOT NULL,
    payload        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_live_runtime_events_session_timestamp
    ON live_runtime_events (session_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_live_runtime_events_severity_timestamp
    ON live_runtime_events (severity, timestamp DESC);

ALTER TABLE live_runtime_events ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')
       AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        EXECUTE 'DROP POLICY IF EXISTS live_runtime_events_deny_api_roles ON live_runtime_events';
        EXECUTE '
            CREATE POLICY live_runtime_events_deny_api_roles
            ON live_runtime_events
            FOR ALL
            TO anon, authenticated
            USING (false)
            WITH CHECK (false)
        ';
    END IF;
END $$;
