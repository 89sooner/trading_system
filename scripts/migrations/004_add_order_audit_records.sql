CREATE TABLE IF NOT EXISTS order_audit_records (
    record_id          TEXT PRIMARY KEY,
    scope              TEXT NOT NULL,
    owner_id           TEXT NOT NULL,
    event              TEXT NOT NULL,
    symbol             TEXT,
    side               TEXT,
    requested_quantity TEXT,
    filled_quantity    TEXT,
    price              TEXT,
    status             TEXT,
    reason             TEXT,
    timestamp          TIMESTAMPTZ NOT NULL,
    payload            JSONB NOT NULL DEFAULT '{}'::jsonb,
    broker_order_id    TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_order_audit_scope_owner_timestamp
    ON order_audit_records (scope, owner_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_order_audit_symbol_timestamp
    ON order_audit_records (symbol, timestamp DESC);

ALTER TABLE order_audit_records ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')
       AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        EXECUTE 'DROP POLICY IF EXISTS order_audit_records_deny_api_roles ON order_audit_records';
        EXECUTE '
            CREATE POLICY order_audit_records_deny_api_roles
            ON order_audit_records
            FOR ALL
            TO anon, authenticated
            USING (false)
            WITH CHECK (false)
        ';
    END IF;
END $$;
