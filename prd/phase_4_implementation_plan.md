# Phase 4 Implementation Plan

## Goal

Replace the 7-page vanilla HTML/JS frontend with a React 19 TypeScript SPA using shadcn/ui on Tailwind CSS v4. All existing pages and operator workflows are preserved. The backend API and localStorage schema are unchanged. One new capability is unlocked: the Trade Analytics view on Run Detail, sourced from the already-implemented but previously unused `GET /api/v1/analytics/backtests/{run_id}/trades` endpoint.

## Assumptions

- The backend API contract (`/api/v1/*` routes, DTOs, ports) is stable and will not change during Phase 4.
- Backend DTOs are fixed for this phase; the frontend must adapt to the existing shapes.
- Operator workstations have Node.js 20+ for `npm run dev`.
- The existing analytics endpoint returns correct data for succeeded runs.
- The vanilla frontend files (`frontend/src/pages/*.js`) remain readable as reference implementations throughout the migration.
- `frontend/` is replaced in-place; no parallel `frontend-v2/` directory.

## Impacted Areas

- `frontend/` — entire directory replaced
- `README.md` — frontend startup section
- `GEMINI.md` — frontend startup section
- `.gitignore` — add `frontend/node_modules/`, `frontend/dist/`

The following vanilla source files must be read before implementing their corresponding routes to avoid behavioral regressions:

| Vanilla file | Informs |
|---|---|
| `frontend/src/api/client.js` | `src/api/client.ts` — ApiError, base-url storage contract, fetch pattern |
| `frontend/src/pages/dashboardPage.js` | Epic D — polling loop, control action, Promise.allSettled pattern |
| `frontend/src/pages/runDetailPage.js` | Epic E — two-chart rendering, summary grid, signals/fills tables |
| `frontend/src/pages/patternsPage.js` | Epic F — `parseExamples()`, two-step train/save workflow |
| `frontend/src/pages/strategiesPage.js` | Epic G — `parseMap()` for label-to-side and threshold textareas |
| `frontend/src/state/runStore.js` | `src/store/runsStore.ts` — localStorage key and max-100-runs schema |

## Implementation Steps

### Step 1. Scaffold

Read the vanilla source files first and keep them available until route parity is verified.

Create the new SPA scaffold in-place without deleting the vanilla implementation yet:
- `frontend/package.json` — all dependencies (see Tech Stack section)
- `frontend/vite.config.ts` — plugins: TanStackRouterVite, react-swc, tailwindcss; `server.port: 5173`; `server.proxy: { '/api': 'http://127.0.0.1:8000' }`; `resolve.alias: { '@': './src' }`
- `frontend/tsconfig.json`, `tsconfig.app.json`, `tsconfig.node.json` — standard Vite React TS config
- `frontend/components.json` — shadcn/ui config: dark theme, zinc palette, `@/` path alias
- `frontend/index.html` — Vite SPA entry: `<div id="root">` only

Run `npm install`. Verify `npm run dev` starts on port 5173 with a blank React app before proceeding.

### Step 2. Core Infrastructure

Create the shared foundation all routes depend on:

- `src/styles/globals.css` — `@import "tailwindcss"` + `@theme` block with trading color tokens (`--color-bull`, `--color-bear`, `--color-warn`, `--color-info`, background, surface, border, text tokens)
- `src/lib/utils.ts` — `cn()` combining clsx and tailwind-merge; required by all shadcn/ui components
- `src/lib/queryClient.ts` — TanStack Query `QueryClient` singleton with default `staleTime: 0`, `gcTime: 5 * 60 * 1000`
- `src/lib/formatters.ts` — verbatim port of `frontend/src/utils/formatters.js` using `Intl.NumberFormat` and `Intl.DateTimeFormat`
- `src/store/apiStore.ts` — Zustand with `persist` middleware; localStorage key `ts_api_base_url`; initial value `http://127.0.0.1:8000/api/v1`; hydrate from legacy `apiBaseUrl` once when the new key is absent
- `src/store/authStore.ts` or equivalent local UI state — optional API Key value for dashboard/API requests
- `src/store/runsStore.ts` — Zustand with `persist` middleware; localStorage key `ts_backtest_runs`; max 100 runs; functions: `listRuns`, `saveRun`, `updateRunStatus`

Add shadcn/ui components via CLI: `button`, `card`, `badge`, `input`, `label`, `select`, `table`, `textarea`, `dialog`, `toast`.

### Step 3. API Layer

Read `frontend/src/api/client.js` carefully before writing any TypeScript.

Create `src/api/client.ts`:
- `ApiError` class with `kind: 'network' | 'validation' | 'server' | 'http'`, `status`, `payload`
- `requestJson<T>(path, options?)` — reads `baseUrl` from `apiStore.getState().baseUrl` at call time (not captured at module load), applies optional `X-API-Key` header from UI state when present

Create typed domain modules matching each backend router:

| Module | Functions | Source route |
|---|---|---|
| `dashboard.ts` | getDashboardStatus, getDashboardPositions, getDashboardEvents(limit), postDashboardControl(action) | `/api/v1/dashboard/*` |
| `backtests.ts` | createBacktestRun(dto), getBacktestRun(runId) | `/api/v1/backtests/*` |
| `analytics.ts` | getBacktestTradeAnalytics(runId) | `/api/v1/analytics/backtests/{runId}/trades` |
| `patterns.ts` | trainPatterns(dto), savePatternSet(dto), listPatternSets(), getPatternSet(id) | `/api/v1/patterns/*` |
| `strategies.ts` | createStrategyProfile(dto), listStrategyProfiles(), getStrategyProfile(id) | `/api/v1/strategies/*` |

All request/response types must match the backend DTOs exactly. Use `src/trading_system/api/schemas.py` as the authoritative shape source, and use route files to confirm endpoint behavior.

### Step 4. Layout and Router Shell

Create the application shell that wraps all routes:

- `src/main.tsx` — `ReactDOM.createRoot`; wrap with `QueryClientProvider` (using the singleton from Step 2) and `RouterProvider`
- `src/routes/__root.tsx` — `AppShell` component: dark header bar with `NavBar` + `ApiSettingsBar` + `<Outlet />`
- `src/components/layout/NavBar.tsx` — links using TanStack Router `<Link>` with `activeProps` for active highlight: New Run | Dashboard | Runs | Patterns | Strategies
- `src/components/shared/StatusBadge.tsx` — variant map: `RUNNING`→bull, `PAUSED`→warn, `EMERGENCY`→bear, `INIT|UNKNOWN`→muted
- `src/components/shared/StatTile.tsx` — label + formatted value; accepts optional `trend` prop (up/down for color)
- `src/components/shared/ErrorBanner.tsx` — renders API errors with kind-appropriate message
- `src/components/shared/ApiSettingsBar.tsx` — single settings widget in header; reads/writes `apiStore.baseUrl` and optional API Key

### Step 5. Dashboard Page

Read `frontend/src/pages/dashboardPage.js` before writing any dashboard component.

Create `src/hooks/useDashboardPolling.ts`:
- Three parallel `useQuery` calls for status, positions, events
- `refetchInterval: 5000`, `refetchIntervalInBackground: false`, `retry: 2`
- Exposes `lastSuccessTime` derived from `dataUpdatedAt` for the `LiveDot`

Create components:
- `StatusCard.tsx` — `StatusBadge` (state) + heartbeat timestamp + uptime seconds + `LiveDot` (green pulse if `Date.now() - lastSuccessTime < 10_000`, else amber)
- `ControlButtons.tsx` — Pause (warn), Resume (bull), Reset (bear); Reset wraps in shadcn `<Dialog>` with "This will clear EMERGENCY and return to PAUSED. Continue?" confirmation text; all three use `startTransition` + `useMutation`-style pattern; on success call `queryClient.invalidateQueries({ queryKey: ['dashboard'] })`
- `PositionsTable.tsx` — shadcn `<Table>` with columns: symbol, quantity, average cost, unrealized PnL (bull/bear colored); footer row for cash
- `EventFeed.tsx` — scrollable feed; severity color map is string-based: `INFO`→info, `WARNING`→warn, `ERROR|CRITICAL`→bear

Create `src/routes/dashboard.tsx`. Renders 503 `ErrorBanner` when `statusQuery.error?.status === 503`.

**Gate**: verify against a running backend before proceeding to Step 6.

### Step 6. Run Detail Page

Read `frontend/src/pages/runDetailPage.js` before writing any component.

Create chart components (confirm Recharts v2 renders correctly with React 19 before building all charts):
- `EquityCurveChart.tsx` — `<AreaChart>` with gradient fill (`--color-info` → transparent); XAxis `type="number" scale="time"`; data: `equity_curve` from `BacktestRunStatusDTO`
- `DrawdownChart.tsx` — `<AreaChart>` with gradient fill (`--color-bear` → transparent); y-axis domain `[min, 0]`; data: `drawdown_curve`
- `TradeScatterChart.tsx` — `<ScatterChart>`; x: `entry_time` (epoch ms), y: `pnl` (number); dots colored bull if `pnl > 0`, bear if `pnl <= 0`; data: `trades` from analytics response

Create run components:
- `RunSummaryGrid.tsx` — six `StatTile` components: return (bull/bear by sign), maxDrawdown (bear), volatility, winRate, startedAt, finishedAt
- `SignalsTable.tsx` — columns: event, symbol, side, quantity, reason
- `FillsTable.tsx` — columns: type, event, symbol, quantity, status; rejections shown in bear color
- `TradesTable.tsx` — columns: entry time, exit time, symbol, qty, entry price, exit price, PnL (bull/bear colored), holding time

Create `src/routes/runs.$runId.tsx`:
- Two `useQuery` calls: `getBacktestRun(runId)` and `getBacktestTradeAnalytics(runId)`
- `staleTime: run.status === 'succeeded' ? Infinity : 10_000` applied to both queries
- Trade Analytics card only renders when analytics query succeeds; if the analytics request fails, keep the rest of the page rendered and show a local degraded-state message

### Step 7. Patterns Pages

Read `frontend/src/pages/patternsPage.js` before writing anything.

Create `src/lib/patternParser.ts` — verbatim port of `parseExamples()`: parses textarea blocks into `PatternExampleDTO[]`. The parsing logic must not be changed; only types are added.

Create components:
- `PatternTrainForm.tsx` — controlled form; local state `latestPreview: PatternSetDTO | null`; "Train Preview" submits POST `/patterns/train` and sets `latestPreview`; "Save Pattern Set" (disabled until `latestPreview !== null`) submits POST `/patterns` then calls `invalidateQueries(['patterns'])`
- `PatternPreviewTable.tsx` — shows `latestPreview.patterns` with columns: label, lookback, sample_size, threshold
- `PatternSetsTable.tsx` — lists all saved sets; each row links to `/patterns/$patternSetId`

Create `src/routes/patterns.tsx` and `src/routes/patterns.$patternSetId.tsx`.

### Step 8. Strategies and Runs List Pages

Read `frontend/src/pages/strategiesPage.js` and `frontend/src/pages/runsPage.js` before writing.

Create `src/lib/strategyParser.ts` — verbatim port of `parseMap()`: parses `key=value` multiline textarea into `Record<string, string>`.

Create:
- `StrategyForm.tsx` — patternSet `<Select>` populated by `useQuery(listPatternSets)`; label-to-side and threshold-overrides as monospace `<Textarea>`; POST `/strategies` on submit
- `StrategiesTable.tsx`
- `src/routes/strategies.tsx`
- `src/hooks/useRunsList.ts` — reads from `runsStore`; `useQueries` for batch `getBacktestRun` per stored runId; calls `updateRunStatus` for each completed query
- `RunsTable.tsx` — columns: runId (truncated), symbol, strategy, status badge, created; rows link to `/runs/$runId`
- `src/routes/runs.tsx`

### Step 9. Create Run Page

Read `frontend/src/pages/createRunPage.js` before writing.

Create `src/routes/index.tsx`:
- Form fields match existing vanilla form: symbol, maxPosition, maxNotional, maxOrderSize, tradeQuantity, feeBps, strategy profile selector
- Strategy selector: `useQuery(listStrategyProfiles, { staleTime: 30_000 })`; renders as shadcn `<Select>`
- Submit uses React 19 `useFormStatus` to disable button and show loading state
- On success: `runsStore.saveRun(run)` then `router.navigate({ to: '/runs/$runId', params: { runId: run.run_id } })`

### Step 10. Cleanup and Documentation

1. After route parity and build verification pass, remove old HTML files and the vanilla `frontend/src/` implementation
2. Add to `.gitignore`:
   ```
   frontend/node_modules/
   frontend/dist/
   ```
3. Commit `frontend/routeTree.gen.ts` — this is auto-generated by TanStack Router at dev-server start; must be committed for reproducible builds
4. Update `README.md`: replace `python -m http.server 5173 -d frontend` with:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
5. Apply the same change to `GEMINI.md`

## Epic Breakdown

### Epic A. Scaffold and Core Infrastructure
Set up Vite, TypeScript, Tailwind v4, Zustand stores, shadcn/ui base components, and TanStack Query client.

### Epic B. API Layer
Port `client.js` to typed TypeScript; add domain modules for all five backend routers.

### Epic C. Layout and Router Shell
App entry point, root route with AppShell, NavBar, and shared display components.

### Epic D. Dashboard Page
Live polling, control buttons with confirmation dialog, positions table, event feed.

### Epic E. Run Detail Page
Equity and drawdown charts, run summary, signals and fills tables, new Trade Analytics card.

### Epic F. Patterns Pages
Pattern train/preview/save workflow and pattern detail.

### Epic G. Strategies and Runs List Pages
Strategy creation form and batch-refreshed runs list.

### Epic H. Create Run Page
Backtest form with React 19 `useFormStatus`.

### Epic I. Cleanup and Documentation
Remove vanilla files; update README and GEMINI; fix .gitignore; commit routeTree.gen.ts.

### Epic J. Verification
End-to-end behavioral verification against a running backend; build verification.

## Test Plan

### Behavioral Verification (manual, against running backend)
- Dashboard: open, confirm polling starts, trigger Pause → state updates, trigger Reset → confirm dialog appears, confirm state changes to PAUSED after reset
- Dashboard: verify API Key input results in `X-API-Key` being sent
- Dashboard: seed legacy `apiBaseUrl` in localStorage and confirm the new app migrates it to `ts_api_base_url`
- Run Detail: open a succeeded run, confirm equity chart, drawdown chart, and Trade Analytics card all render with real data
- Run Detail: confirm signals and fills render without timestamp assumptions and match current API payloads
- Patterns: train a preview, save it, navigate to detail page, confirm data matches what was saved
- Strategies: create a profile, confirm it appears in the list and in the Create Run form selector
- Runs List: create a new run, confirm it appears in the list with correct status, click through to run detail
- LocalStorage backward compatibility: confirm `ts_backtest_runs` is preserved and legacy `apiBaseUrl` is migrated correctly

### Build Verification
- `npm run build` completes with zero TypeScript errors
- `npm run preview` serves `dist/` and all routes load correctly

## Risks and Follow-Up

- If Recharts has compatibility issues with React 19 Suspense, wrap chart components in an error boundary and fall back to a "Charts unavailable" message rather than blocking the page render.
- If `routeTree.gen.ts` is large or frequently regenerated, add a CI step to regenerate it as part of the build rather than requiring manual commits.
- If the production deployment does not include a proxy, add `VITE_API_BASE_URL` environment variable support to `apiStore` so the base URL can be set at build time rather than relying on the Vite dev proxy.
- If the legacy dashboard `apiBaseUrl` key is ignored instead of migrated, operators can lose saved endpoint settings at cutover.
- If API Key support is omitted from the shared settings UI, protected dashboard deployments will regress.
- If vanilla `parseExamples()` or `parseMap()` contain edge cases not covered by the exploration, treat the vanilla source as the authoritative spec and match it exactly rather than simplifying.
