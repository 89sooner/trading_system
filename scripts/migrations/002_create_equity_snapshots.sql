CREATE TABLE IF NOT EXISTS equity_snapshots (
    id              BIGSERIAL PRIMARY KEY,
    session_id      TEXT NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL,
    equity          NUMERIC,
    cash            NUMERIC,
    positions_value NUMERIC,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_equity_snapshots_session_ts
    ON equity_snapshots (session_id, timestamp DESC);

ALTER TABLE equity_snapshots ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')
       AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        EXECUTE 'DROP POLICY IF EXISTS equity_snapshots_deny_api_roles ON equity_snapshots';
        EXECUTE '
            CREATE POLICY equity_snapshots_deny_api_roles
            ON equity_snapshots
            FOR ALL
            TO anon, authenticated
            USING (false)
            WITH CHECK (false)
        ';
    END IF;
END $$;
