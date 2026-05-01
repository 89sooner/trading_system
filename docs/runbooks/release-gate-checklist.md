# Release Gate Checklist

## Purpose

Use a single operational standard before enabling live order submission.
In the current repository, `--mode live` defaults to preflight, and `--live-execution paper` runs the paper loop without submitting real orders.
The KIS live-order path exists, but it is explicitly gated behind `TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true`.

## Gate 1: Test baseline

- [ ] `uv run --python .venv/bin/python --no-sync pytest -m smoke -q` passes
- [ ] `uv run --python .venv/bin/python --no-sync pytest -m "not smoke" -q` passes
- [ ] Recent changes in config, risk, and execution boundaries include new regression coverage

## Gate 2: Config and secret baseline

- [ ] `configs/base.yaml` matches the current `config.settings.load_settings()` schema
- [ ] If `portfolio_risk` is used, the injection path is documented through API payloads, app runtime settings, or typed YAML config (`configs/base.yaml`, `examples/sample_live_kis.yaml`)
- [ ] Production environment injection for `TRADING_SYSTEM_API_KEY` or KIS credentials is confirmed
- [ ] No secrets are exposed in code, logs, or tickets

## Gate 3: Runtime preflight baseline

- [ ] `TRADING_SYSTEM_API_KEY=dummy-key uv run --python .venv/bin/python --no-sync -m trading_system.app.main --mode live --symbols BTCUSDT` succeeds
- [ ] `TRADING_SYSTEM_API_KEY=dummy-key uv run --python .venv/bin/python --no-sync -m trading_system.app.main --mode live --symbols BTCUSDT --live-execution paper` succeeds
- [ ] If transitioning to KIS live orders, preflight succeeds with `--provider kis --broker kis`
- [ ] Invalid configuration inputs return clear user-facing errors
- [ ] Operators understand the multi-symbol capabilities of the backtest/live loop and the backward-compatible `/api/v1/live/preflight` response shape (`quote_summary` vs `quote_summaries`/`symbol_count`)
- [ ] If the dashboard will be used, deployment is ready to start the API server with an attached live loop
- [ ] Durable backtest worker smoke passes with `python scripts/backtest_worker_smoke.py`
- [ ] Supabase environments have applied `scripts/migrations/006_add_backtest_jobs.sql`; `python scripts/check_supabase_backtest_jobs.py` passes before starting API or worker processes

## Gate 4: Incident drill baseline

- [ ] Data disconnect scenario reviewed (incident-response scenario A)
- [ ] Risk rejection / emergency scenario reviewed (incident-response scenario B)
- [ ] Order failure / broker error scenario reviewed (incident-response scenario C)
- [ ] If the environment uses broker snapshots, reconciliation mismatch scenario reviewed (incident-response scenario D)
- [ ] Live order audit is verified without relying on `TestClient(create_app())` lifespan startup (`pytest tests/integration/test_order_audit_integration.py -q`)
- [ ] KIS open-order pending authority is covered by parser and reconciliation tests
- [ ] Historical live session review is verified through `/api/v1/live/runtime/sessions/<session_id>/evidence` and the `/dashboard/sessions` route

## Gate 5: Sign-off

- [ ] Engineering owner approval
- [ ] Operations owner approval
- [ ] Rollback owner and contact channel confirmed

## Notes

- Even though the KIS live-order path exists, do not enable `TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true` until all gates are complete.
- Generic reconciliation works when the broker exposes account balance snapshots. The KIS adapter now prefers open-order snapshots for pending authority and skips fail-closed if that source is unavailable or malformed.
