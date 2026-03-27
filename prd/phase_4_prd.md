# Product Requirements Document (PRD) - Phase 4

## 1. Overview

Phase 3.5 closed the production-readiness gaps in the backend runtime and operator documentation. The system now has a stable, well-tested backend with a reliable dashboard control contract.

Phase 4 does not extend the backend. It replaces the existing 7-page vanilla HTML/JS frontend with a React 19 TypeScript single-page application. The replacement uses the dominant React design system as of 2026 (shadcn/ui on Tailwind CSS v4) and surfaces an existing but unused analytics endpoint as a new Trade Analytics view. The operator workflow remains equivalent, while the backend API contract remains unchanged and frontend storage is standardized with explicit legacy-key migration.

## 2. Product Goals

### Goal 1. Modern Operator Interface
Replace the vanilla HTML UI with a dark-mode, professionally-styled trading dashboard. shadcn/ui on Tailwind CSS v4 provides a component-owned, fully customizable design system with trading-appropriate color semantics (bull/bear/warn/info).

### Goal 2. Developer Maintainability
Introduce TypeScript, React 19, TanStack Router v1, and TanStack Query v5 so the frontend is type-safe, component-driven, and testable. The file-based router provides compile-time typed path and search params.

### Goal 3. Surface Existing But Hidden Analytics
`GET /api/v1/analytics/backtests/{run_id}/trades` is fully implemented in the backend but was never called by the vanilla frontend. Phase 4 adds a Trade Analytics card with a scatter chart and trades table to the Run Detail page.

### Goal 4. Preserve Operator Continuity
- `localhost:5173` remains the frontend port (Vite dev server replaces `python -m http.server 5173 -d frontend`)
- localStorage key `ts_backtest_runs` is preserved with identical semantics
- legacy dashboard key `apiBaseUrl` is automatically migrated to `ts_api_base_url`
- All 7 pages preserve the existing operator flows; Run Detail additionally surfaces Trade Analytics

## 3. Detailed Requirements

### 3.1 Tech Stack

| Concern | Choice | Reason |
|---|---|---|
| Framework | React 19 + TypeScript | Latest stable; Actions, `use()`, `useFormStatus` built-in |
| Design system | shadcn/ui + Tailwind CSS v4 | Copy-owned components, zero lock-in, dark-mode CSS variables, Radix UI accessibility primitives |
| Build tool | Vite 6 + `@vitejs/plugin-react-swc` | Port 5173 continuity, `@tailwindcss/vite` native plugin, fast HMR |
| Router | TanStack Router v1 | Compile-time typed path + search params; file-based routes |
| Data fetching | TanStack Query v5 | `refetchInterval` for polling, `useQueries` for batch status refresh, `staleTime: Infinity` for immutable runs |
| State | Zustand v5 + persist | Direct drop-in for two localStorage entries; no boilerplate |
| Charts | Recharts v2 | Pure React SVG, concurrent-safe, direct data-shape match to existing DTOs |
| Icons | lucide-react | Standard shadcn/ui companion library |

### 3.2 Route Parity

All 7 vanilla pages must be implemented as typed React routes with identical behavior.

| Vanilla page | New route | Key behavior |
|---|---|---|
| `index.html` | `/` | Backtest form; React 19 `useFormStatus`; navigate to `/runs/$runId` on success |
| `dashboard.html` | `/dashboard` | 5-second polling; Pause/Resume/Reset controls; Reset requires Dialog confirmation; API Base URL + API Key settings preserved |
| `patterns.html` | `/patterns` | Two-step train → save; `parseExamples()` ported to `lib/patternParser.ts` |
| `pattern.html?pattern_set_id=X` | `/patterns/$patternSetId` | Immutable detail; `staleTime: Infinity` |
| `strategies.html` | `/strategies` | `parseMap()` for label-to-side and threshold textareas |
| `runs.html` | `/runs` | Batch status refresh via `useQueries`; Zustand run list |
| `run.html?run_id=X` | `/runs/$runId` | Equity + drawdown charts; existing summary/signals/fills preserved under current DTOs; Trade Analytics card (new) |

### 3.3 Dashboard Polling

- Three `useQuery` calls with `refetchInterval: 5000` and `refetchIntervalInBackground: false` replace `setInterval` in `dashboardPage.js`
- `LiveDot` component pulses green when last poll succeeded within 10 seconds, turns amber when stale or errored
- Control buttons use React 19 `startTransition`; after action `queryClient.invalidateQueries(['dashboard'])` triggers immediate refetch
- `reset` button renders a shadcn/ui `<Dialog>` confirmation (matching existing `confirm()` semantics)
- Dashboard continues to support optional API Key entry and sends `X-API-Key` when present
- Dashboard settings standardize on `ts_api_base_url` while automatically migrating the legacy `apiBaseUrl` key on first load
- Backend 503 (no loop running) renders a persistent `ErrorBanner` replacing the status card

### 3.4 Trade Analytics (new)

- Run Detail page calls `GET /api/v1/analytics/backtests/{run_id}/trades`
- `staleTime: Infinity` for runs with `status === 'succeeded'`
- New components: `TradeScatterChart` (PnL vs. entry time, green/red by win/loss), `TradesTable`, analytics stat tiles
- Must not merge trade data into the equity-curve summary response — the dedicated analytics endpoint is the source

### 3.5 Dark Mode

Dark-first; no toggle. Tailwind v4 `@theme` block in `globals.css` defines trading semantic tokens:

```
--color-bull:  #22c55e   (gains, RUNNING state, buy side)
--color-bear:  #ef4444   (losses, EMERGENCY state, sell side)
--color-warn:  #f59e0b   (PAUSED state, warnings)
--color-info:  #3b82f6   (equity curve, INFO events)
```

### 3.6 Build and Serve

- `npm run dev` → Vite on port 5173 (replaces `python -m http.server 5173 -d frontend`)
- `npm run build` → `dist/` deployable as a pure static site
- Vite dev proxy: `/api` → `http://127.0.0.1:8000` (eliminates CORS in development without touching the backend)
- Operator startup sequence is unchanged: start backend with `uvicorn`, then `npm run dev` in `frontend/`

### 3.7 State Migration

- Zustand `apiStore` → localStorage key `ts_api_base_url`
- Zustand `runsStore` → localStorage key `ts_backtest_runs`, max 100 runs (unchanged)
- On app startup, if legacy `apiBaseUrl` exists and `ts_api_base_url` is absent, migrate the value once and then use `ts_api_base_url`
- `ApiSettingsBar` moves from a repeated per-page section to a single widget in the app header and includes both API Base URL and optional API Key

## 4. Non-Functional Requirements

- Backend API is unchanged: all `/api/v1/*` routes, response shapes, and ports remain as-is
- Backend DTOs are unchanged: Phase 4 must not add fields such as timestamps to run events
- localStorage compatibility is preserved through explicit migration, not dual-write permanence
- Port 5173 is preserved so operator documentation and startup scripts need no changes
- Build output must be deployable as a pure static site; no SSR required
- Desktop-first layout acceptable; mobile responsive is out of scope

## 5. Scope

### In Scope
- Full replacement of the `frontend/` directory contents
- All 7 routes with feature parity to the vanilla pages
- New Trade Analytics card in Run Detail page (using the existing analytics endpoint)
- Dark-mode design system implementation
- Legacy `apiBaseUrl` migration to `ts_api_base_url`
- Dashboard API Key workflow preservation
- `README.md` and `GEMINI.md` frontend section updates (replace `python -m http.server` with `npm run dev`)

### Out Of Scope
- Backend changes of any kind
- WebSocket or SSE upgrades (polling remains sufficient)
- New API endpoints
- Light mode toggle
- Mobile responsive layout

## 6. Success Criteria

- All 7 routes render correctly and behave identically to the vanilla pages against a running backend
- Dashboard polls status, positions, and events every 5 seconds; control actions reflect state immediately
- Dashboard preserves optional API Key entry and sends `X-API-Key` when configured
- Run Detail page shows equity curve, drawdown curve, and Trade Analytics card sourced from the analytics endpoint
- Run Detail summary, signals, and fills render strictly from the current backend DTO shape
- `reset` control shows a confirmation dialog before posting; EMERGENCY badge renders in bear color
- `npm run build` completes without TypeScript errors and `dist/` is deployable
- Existing localStorage data (`ts_backtest_runs` and legacy `apiBaseUrl`) is handled correctly after migration
- Dark mode renders correctly in Chrome and Firefox

## 7. Risks and Assumptions

### Assumptions
- Backend API contract (routes, DTOs, ports) is stable and will not change during Phase 4
- Operator workstations have Node.js 20+ available for `npm run dev`
- The existing analytics endpoint is complete and returns valid trade data for succeeded runs
- The current run event DTOs do not contain timestamps, and the frontend must not invent backend fields

### Risks
- Recharts' compatibility with React 19 concurrent rendering and Suspense boundaries must be verified early in Step 6
- TanStack Router file-based codegen produces `routeTree.gen.ts`; this file must be committed rather than gitignored to keep the build reproducible
- Vite proxy handles CORS in development; production deployments need either a static host with proxy configuration or CORS enabled on the backend
- If legacy `apiBaseUrl` migration is omitted, dashboard users can lose saved endpoint settings during the cutover
- If API Key input is dropped from the new dashboard, protected deployments will regress operationally
- If any vanilla page contains behavior not captured in the exploration, it will surface as a regression; the vanilla `src/pages/*.js` files must be read carefully before each route implementation
