CREATE TABLE IF NOT EXISTS live_order_lifecycle (
    record_id           TEXT PRIMARY KEY,
    session_id          TEXT NOT NULL,
    symbol              TEXT NOT NULL,
    side                TEXT NOT NULL,
    requested_quantity  TEXT NOT NULL,
    filled_quantity     TEXT NOT NULL,
    remaining_quantity  TEXT NOT NULL,
    status              TEXT NOT NULL,
    broker_order_id     TEXT,
    submitted_at        TIMESTAMPTZ NOT NULL,
    last_synced_at      TIMESTAMPTZ,
    stale_after         TIMESTAMPTZ,
    cancel_requested    BOOLEAN NOT NULL DEFAULT FALSE,
    cancel_requested_at TIMESTAMPTZ,
    cancelled_at        TIMESTAMPTZ,
    last_error          TEXT,
    payload             JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_live_order_lifecycle_session_status
    ON live_order_lifecycle (session_id, status, submitted_at DESC);

CREATE INDEX IF NOT EXISTS idx_live_order_lifecycle_broker_order
    ON live_order_lifecycle (broker_order_id)
    WHERE broker_order_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_live_order_lifecycle_stale
    ON live_order_lifecycle (status, stale_after)
    WHERE stale_after IS NOT NULL;

ALTER TABLE live_order_lifecycle ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')
       AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        EXECUTE 'DROP POLICY IF EXISTS live_order_lifecycle_deny_api_roles ON live_order_lifecycle';
        EXECUTE '
            CREATE POLICY live_order_lifecycle_deny_api_roles
            ON live_order_lifecycle
            FOR ALL
            TO anon, authenticated
            USING (false)
            WITH CHECK (false)
        ';
    END IF;
END $$;
