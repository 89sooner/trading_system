# Current System User Use Cases

This document summarizes the user-facing use cases supported by the current `trading_system` workspace as of April 19, 2026.

## 1. Scope

The current system is not a single end-user trading product. It is a modular trading workspace with three main entry points:

- CLI runtime for backtest and live execution
- HTTP API for backtest, live preflight, analytics, pattern management, strategy management, and dashboard control
- React frontend for pattern/strategy management, backtest execution, run review, and live dashboard monitoring

The system is designed for operators, researchers, and developers rather than anonymous retail end users.

## 2. Primary user roles

### 2.1 Strategy researcher

The strategy researcher creates reusable pattern definitions, maps pattern labels to trade actions, and validates ideas with deterministic backtests.

### 2.2 Trading operator

The trading operator runs live preflight checks, starts paper or live execution, monitors runtime state, and reacts to emergency or paused conditions.

### 2.3 API or frontend consumer

The API/frontend consumer uses the HTTP API and web UI to manage saved artifacts and inspect results without working directly inside Python modules.

### 2.4 Developer or system integrator

The integrator connects the workspace to infrastructure, configures API keys/CORS/rate limits, and starts the API or runtime processes in the correct mode.

## 3. System entry points

| Entry point | Primary purpose | Typical user |
| --- | --- | --- |
| `trading_system.app.main` | Run backtest or live execution from CLI | Operator, developer |
| `/api/v1/backtests` | Start deterministic backtest and fetch run result | Frontend, API client |
| `/api/v1/backtests/dispatcher` | Inspect durable backtest queue, worker heartbeat, and stale lease state | Operator |
| `/api/v1/backtests/retention/*` | Preview and prune old run records | Operator, integrator |
| `/api/v1/order-audit` | Query order audit records by backtest run or live session | Operator, researcher |
| `/api/v1/order-audit/export` | Export order audit records by owner/time/status/broker id as CSV or JSONL | Operator, integrator |
| `/api/v1/live/preflight` | Validate live runtime path before or during execution mode selection | Operator, integrator |
| `/api/v1/live/runtime/sessions` | Search, filter, and inspect live runtime session history | Operator, integrator |
| `/api/v1/live/runtime/sessions/export` | Export live runtime session history as CSV or JSONL | Operator, integrator |
| `/api/v1/live/runtime/sessions/{session_id}/evidence` | Inspect session-scoped equity/order-audit/incident evidence | Operator, integrator |
| `/api/v1/patterns` | Train, save, list, and inspect pattern sets | Researcher |
| `/api/v1/strategies` | Save and retrieve reusable strategy profiles | Researcher |
| `/api/v1/analytics/backtests/{run_id}/trades` | Inspect trade-level analytics for a completed run | Researcher |
| `/api/v1/dashboard/*` | Monitor and control the active live loop | Operator |
| Frontend routes `/`, `/patterns`, `/strategies`, `/runs`, `/dashboard` | Browser-based workflow over the API | Researcher, operator |

## 4. Core artifacts users interact with

| Artifact | Stored at | Purpose |
| --- | --- | --- |
| Pattern set | `configs/patterns/*.json` | Reusable learned pattern definitions |
| Strategy profile | `configs/strategies/*.json` | Reusable mapping from pattern labels to actions |
| Portfolio snapshot | `data/portfolio/book.json` | Restart-safe live portfolio state |
| Backtest run result + metadata | File repository or Supabase-backed PostgreSQL | Durable run lookup, review context, and analytics |
| Live runtime session history | File repository or Supabase-backed PostgreSQL | Live session search, export, and post-run review |
| Live runtime event archive | File repository or Supabase-backed PostgreSQL | Session-scoped incident review for warning/error/risk/reconciliation/control events |
| Order audit records | File repository or Supabase-backed PostgreSQL | Query order creation, fills, rejections, and risk rejections by run/session owner |
| Frontend run history fallback | Browser local storage | Fallback cache when the backend is unavailable |

## 5. End-to-end user journey

The intended high-value workflow today is:

1. Define labeled chart examples and train a pattern preview.
2. Save the pattern set to the repository-backed config directory.
3. Create a reusable strategy profile that maps pattern labels to `buy`, `sell`, or `hold`.
4. Start a deterministic backtest using the saved strategy profile.
5. Review run summary, equity curve, drawdown, fills, rejections, and trade analytics.
6. Run live preflight to verify credentials and runtime readiness without uncontrolled order submission.
7. Move to paper execution, then optionally to live KIS order submission with explicit environment opt-in.
8. Monitor the live loop from the dashboard and use `pause`, `resume`, or `reset` when needed.

## 6. Detailed use cases

### UC-01. Train a pattern set preview

- User: strategy researcher
- Goal: turn manually curated bar sequences into a candidate pattern set before saving it
- Entry points:
  - frontend `/patterns`
  - `POST /api/v1/patterns/train`
- Preconditions:
  - the user has at least one labeled example
  - each example has at least two bars
  - timestamps are valid ISO datetime strings
- Main flow:
  1. The user enters a pattern name, symbol, threshold, and labeled examples.
  2. The system groups examples by label.
  3. It extracts feature vectors from each example window.
  4. It averages vectors into a learned prototype per label.
  5. It returns a preview pattern set with `pattern_set_id`, `examples_count`, and learned patterns.
- Outputs:
  - unsaved preview returned to the caller
  - preview table in the frontend
- Current constraints:
  - training is based on manually entered examples, not historical bulk datasets
  - all examples for one label must use the same lookback length
  - training does not persist anything until a separate save step is executed

### UC-02. Save and reuse a pattern set

- User: strategy researcher
- Goal: persist a learned pattern set so it can be reused by strategies
- Entry points:
  - frontend `/patterns`
  - `POST /api/v1/patterns`
  - `GET /api/v1/patterns`
  - `GET /api/v1/patterns/{pattern_set_id}`
- Preconditions:
  - a valid pattern preview or payload exists
- Main flow:
  1. The user saves the trained preview.
  2. The repository writes JSON under `configs/patterns`.
  3. Saved pattern sets become available in listing and detail views.
- Outputs:
  - persistent pattern JSON file
  - pattern detail view showing threshold, sample count, and prototypes
- Current constraints:
  - versioning and approval flow for pattern sets do not exist
  - pattern sets are stored as files, so concurrent editing and lifecycle management are still simple

### UC-03. Create a strategy profile from a pattern set

- User: strategy researcher
- Goal: define how learned pattern labels translate into actual trading actions
- Entry points:
  - frontend `/strategies`
  - `POST /api/v1/strategies`
  - `GET /api/v1/strategies`
  - `GET /api/v1/strategies/{strategy_id}`
- Preconditions:
  - at least one saved pattern set exists
  - the user provides at least one label-to-side mapping
- Main flow:
  1. The user selects a saved pattern set.
  2. The user defines `label_to_side` mappings such as `bullish=buy`.
  3. The user can optionally override per-label thresholds and trade quantity.
  4. The system stores the strategy profile JSON under `configs/strategies`.
- Outputs:
  - reusable strategy profile referenced by `strategy_id`
- Current constraints:
  - stored profiles must use inline pattern strategy settings, not nested profile references
  - only `pattern_signal` strategy type is supported by the API/UI flow

### UC-04. Run a deterministic backtest

- User: strategy researcher or API consumer
- Goal: validate strategy behavior under deterministic replay
- Entry points:
  - frontend `/`
  - CLI `--mode backtest`
  - `POST /api/v1/backtests`
- Preconditions:
  - market data provider is available: `mock`, `csv`, or `kis`
  - risk and backtest parameters are valid
  - if using a pattern strategy, the referenced pattern set or strategy profile exists
- Main flow:
  1. The user submits symbols, sizing, fee, and risk limits.
  2. Services are built with strategy, provider, broker simulator or KIS adapter, portfolio, and logging.
  3. Historical or mock bars are loaded and merged by timestamp.
  4. Each bar runs through the unified execution step:
     strategy evaluation -> signal -> order mapping -> risk check -> broker fill -> portfolio update.
  5. Equity points, orders, signals, and risk rejections are collected.
  6. Order creation, fills, rejections, and risk rejections are stored as order audit records owned by the run.
  7. The API stores a durable job record, and the dispatcher or CLI worker claims it and updates the run as `queued`, `running`, `succeeded`, `failed`, or `cancelled`.
- Outputs:
  - summary return metrics
  - equity curve
  - drawdown curve
  - signal, order, and rejection event streams
- Current constraints:
  - the API-owned dispatcher and standalone CLI worker use the same durable job contract, but there is still no external queue service or partial-result resume
  - persistence depends on deployment configuration: file-backed by default, Supabase-backed when `DATABASE_URL` is set
  - the frontend new-run page accepts a single symbol input even though backtest internals can handle multiple symbols
  - the CLI path does not currently expose pattern-profile selection flags

### UC-05. Review backtest results and trade analytics

- User: strategy researcher
- Goal: understand whether a run is worth iterating on or promoting
- Entry points:
  - frontend `/runs`
  - frontend `/runs/{runId}`
  - `GET /api/v1/backtests/{run_id}`
  - `GET /api/v1/analytics/backtests/{run_id}/trades`
- Preconditions:
  - a backtest run exists, has succeeded, and is still available in the configured repository
- Main flow:
  1. The user opens run history or a run detail page.
  2. The system loads the stored run result.
  3. If the run succeeded, trade extraction and summary statistics are computed from order events.
  4. The frontend renders summary tiles, charts, signals, fills/rejections, and trade tables.
- Outputs:
  - run-level summary: return, drawdown, volatility, win rate
  - trade-level summary: trade count, win rate, risk/reward, max drawdown, average hold time
- Current constraints:
  - the server repository is now the primary run history source, but the browser still keeps a small fallback cache for unavailable-backend cases
  - run review now includes route and strategy metadata, but there is still no broader promotion/approval workflow

### UC-06. Run live preflight safely

- User: trading operator
- Goal: confirm that live runtime dependencies and credentials are valid before meaningful execution
- Entry points:
  - CLI `--mode live --live-execution preflight`
  - `POST /api/v1/live/preflight`
- Preconditions:
  - required credentials exist
  - KIS credentials are set when provider or broker is `kis`
  - at least one symbol is supplied for live API runtime
- Main flow:
  1. The user requests live mode in preflight.
  2. The system validates runtime settings and required secrets.
  3. If KIS is used, it performs per-symbol quote preflight.
  4. The system returns a success message and does not submit orders.
- Outputs:
  - operator-readable preflight pass/fail message
- Current constraints:
  - legacy consumers may still assume a single `quote_summary` field and should migrate to `quote_summaries`/`symbol_count` for multi-symbol detail
  - preflight validates the route to the provider/broker but is not a full exchange or deployment readiness checklist

### UC-07. Run live paper execution

- User: trading operator
- Goal: execute the live loop with realistic state transitions without sending real orders
- Entry points:
  - CLI `--mode live --live-execution paper`
  - `POST /api/v1/live/preflight` with `live_execution=paper`
- Preconditions:
  - live preflight passes
  - a provider and broker path are available
- Main flow:
  1. The live loop starts in `RUNNING`.
  2. On each poll interval, new bars are loaded for configured symbols.
  3. The unified trading step updates marks, evaluates risk, emits signals, and simulates fills.
  4. Portfolio state is saved to `data/portfolio/book.json`.
  5. Heartbeat and runtime events are emitted for dashboard inspection.
- Outputs:
  - continuous portfolio state
  - recent event stream
  - restart-safe saved portfolio snapshot
- Current constraints:
  - past live sessions can be searched and reviewed from `/dashboard/sessions`, but old session retention/prune policy is not yet implemented
  - paper execution shares the same loop mechanics as live, while the API process now owns one active runtime session at a time
  - live dashboard access still depends on the active loop being attached to `app.state.live_loop`

### UC-08. Submit real live orders through KIS

- User: trading operator
- Goal: move from paper execution to real broker submission with explicit safeguards
- Entry points:
  - CLI `--mode live --provider kis --broker kis --live-execution live`
  - `POST /api/v1/live/preflight` with `live_execution=live`
- Preconditions:
  - provider and broker are both `kis`
  - KIS credentials are present
  - `TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true`
  - sample size for KIS live bars resolves to at least 2
- Main flow:
  1. The user explicitly opts in to live execution.
  2. The system validates KIS-only routing and the live-order environment switch.
  3. The live loop continues to use the unified step path, but the broker delegate is the KIS adapter.
  4. Orders can be submitted through the broker adapter rather than only the simulator.
- Outputs:
  - real broker-side order flow through the KIS adapter
  - persistent portfolio state and structured event logging
- Current constraints:
  - live order submission is intentionally hard-gated
  - operational protections such as richer lifecycle recovery, alert routing, and durable order state are still limited

### UC-09. Monitor and control the live runtime

- User: trading operator
- Goal: inspect runtime health and intervene without modifying code
- Entry points:
  - frontend `/dashboard`
  - `GET /api/v1/dashboard/status`
  - `GET /api/v1/dashboard/positions`
  - `GET /api/v1/dashboard/events`
  - `GET /api/v1/dashboard/equity`
  - `GET /api/v1/dashboard/stream`
  - `POST /api/v1/dashboard/control`
- Preconditions:
  - an API server is running with a live loop attached
- Main flow:
  1. The dashboard loads server-side equity history and opens an SSE stream for live updates.
  2. If the SSE connection drops, the UI falls back to 5-second polling for status, positions, and events.
  3. The operator inspects loop state, heartbeat freshness, cash, positions, unrealized PnL, recent events, and the equity curve.
  4. The operator can send `pause`, `resume`, or `reset`.
  5. The system applies only valid state transitions and logs control events.
- Outputs:
  - real-time operational visibility
  - limited runtime control surface
- Current constraints:
  - `reset` only clears `EMERGENCY` to `PAUSED`
  - invalid or no-op transitions return success with current state
  - there is no direct `stop`, `liquidate-all`, or parameter-edit control in the dashboard

### UC-10. Consume the system as a secured internal API

- User: API consumer or integrator
- Goal: use the workspace from other tools while preserving basic operational safety
- Entry points:
  - all HTTP API routes
- Preconditions:
  - API server is running under the project environment
  - caller has the API key when API key enforcement is enabled
- Main flow:
  1. The caller sends requests to the FastAPI server.
  2. Middleware applies CORS rules, correlation IDs, API key validation, and simple rate limiting.
  3. Route handlers return typed DTOs for success and structured bodies for validation/runtime errors.
- Outputs:
  - stable JSON responses for UI or automation clients
- Current constraints:
  - security is appropriate for internal service boundaries, not yet for hardened internet-facing deployment
  - rate limiting is in-process memory based

## 7. Cross-cutting behavior users should expect

### 7.1 Unified execution path

Both backtest and live execution depend on the same `execute_trading_step` flow. This means strategy evaluation, risk checks, order mapping, and portfolio mutation behave consistently across simulation and live-oriented runtime paths.

### 7.2 Safety defaults

The system defaults to the safest available runtime posture:

- CLI live mode defaults to `preflight`
- real live orders require explicit `live` mode plus an environment switch
- dashboard control can pause or recover from emergency, but not silently force the system back into live trading

### 7.3 Deterministic and inspectable outputs

Backtest results are designed to be inspectable rather than opaque:

- event streams are serialized
- numeric fields are stringified consistently for JSON transport
- charts and summary tiles are reconstructed from typed DTOs

## 8. Current product boundaries and gaps

The current implementation is strong for research, controlled paper trading, and operator-oriented monitoring, but it is not yet a full production trading platform.

Key gaps users must account for:

- no external queue/distributed worker model for long-running backtests
- no multi-user auth model beyond shared API key validation
- no advanced order lifecycle dashboard or broker-specific unresolved-order controls
- no strategy marketplace, approval workflow, or promotion pipeline
- built-in order audit export is a bounded CSV/JSONL response, not a large asynchronous export pipeline

## 9. Recommended documentation follow-ups

The next docs that would add the most operator value are:

1. A live deployment guide showing how to start the API server and live loop together.
2. A pattern-authoring guide with example input formats and labeling conventions.
3. A promotion checklist from pattern preview -> saved strategy -> backtest -> paper -> live.
