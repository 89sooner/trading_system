# Incident Runbook

## Scope

Classify and recover incidents quickly across operational boundary layers (`app`, `api`, `data`, `execution`, `portfolio`).
All logs are expected to use a structured format (JSON or key-value) and include a `correlation_id`.

## Common checks

1. Review `system.error`, `system.heartbeat`, `system.control`, `order.created`, `order.rejected`, `order.filled`, `risk.rejected`, `risk.daily_limit_breached`, and `portfolio.reconciliation.*` events in time order using the same `correlation_id`.
2. Confirm that sensitive fields (`api_key`, `token`, `password`, `secret`) are masked as `***`.
3. Check retry, timeout, and circuit-breaker status for external I/O boundaries such as data providers and broker adapters.
4. If a dashboard is attached, compare `/api/v1/dashboard/status` and `/api/v1/dashboard/events` output against the log stream.

## Scenario A: data disconnect

Symptoms:

- `data.load.success` events stop appearing
- `system.error` starts showing CSV, KIS, or broker-call related failures
- live preflight or paper loops pause repeatedly

Response:

1. Check data-source accessibility first: file path, network, permissions.
2. Check whether the circuit breaker is open. If so, wait for `reset_timeout_seconds` before retrying.
3. For KIS paths, also validate credentials, `TRADING_SYSTEM_KIS_BASE_URL`, `TRADING_SYSTEM_KIS_MARKET_DIV`, and network reachability.
4. Do not skip the affected interval. Recollect the missing data and rerun to preserve determinism.

## Scenario B: risk rejection or emergency state

Symptoms:

- `risk.rejected` increases sharply
- `risk.daily_limit_breached`, `risk.emergency_liquidation`, `risk.sl_triggered`, or `risk.tp_triggered` events appear
- dashboard state remains `EMERGENCY` or `PAUSED`

Response:

1. Separate `risk.rejected` from `order.rejected` first so you know whether the issue is a risk guard or an execution failure.
2. Review `requested_quantity`, `current_position`, and `price` in `risk.rejected` payloads against `max_position`, `max_notional`, and `max_order_size`.
3. If `risk.daily_limit_breached` fired, inspect current session peak equity and the loss path before using `reset`.
4. If `sl_pct` or `tp_pct` is enabled, confirm that average-cost and mark-price calculations match operator expectations.

## Scenario C: order failure or broker error

Symptoms:

- `order.rejected` increases
- `system.error` shows broker submission failures, timeouts, or HTTP/transport errors
- `order.created` appears, but `order.filled` is lower than expected

Response:

1. On simulator paths, confirm whether `order.rejected` means `unfilled` and recheck fill-policy settings.
2. On KIS paths, inspect credentials, `tr_id`, network health, base URL, and market-division settings.
3. After retries or timeouts, verify with the broker that duplicate orders were not actually submitted.
4. If the cause is still unclear, `pause` the runtime from the dashboard and collect logs before resuming.

## Scenario D: reconciliation mismatch

Symptoms:

- `portfolio.reconciliation.cash_adjusted`
- `portfolio.reconciliation.position_adjusted`
- `portfolio.reconciliation.cash_frozen`
- `portfolio.reconciliation.symbol_skipped`

Response:

1. First confirm that the active broker path actually provides account balance snapshots.
2. If `cash_frozen` or `symbol_skipped` appears, inspect the `pending_symbols` list for in-flight orders.
3. If a position difference cannot be explained, `pause` the loop and compare the local `PortfolioBook` against broker state manually.
4. The current KIS adapter does not expose account balance snapshots, so do not expect automatic exchange-balance sync in KIS environments today.

## Secret-handling rules

- Inject API keys only through environment variables such as `TRADING_SYSTEM_API_KEY` or through a secret manager.
- Inject KIS credentials only through `TRADING_SYSTEM_KIS_APP_KEY`, `TRADING_SYSTEM_KIS_APP_SECRET`, `TRADING_SYSTEM_KIS_CANO`, and `TRADING_SYSTEM_KIS_ACNT_PRDT_CD`.
- Do not leave secrets in the repository, config files, logs, or tickets.
