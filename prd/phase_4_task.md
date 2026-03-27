# Phase 4 Task Breakdown

## Epic A - Scaffold and Core Infrastructure

- [x] Create `frontend/package.json` with React 19, TanStack Router v1, TanStack Query v5, Zustand v5, Recharts v2, shadcn/ui Radix primitives, lucide-react, Tailwind CSS v4, Vite 6
- [x] Create `frontend/vite.config.ts` (plugins: TanStackRouterVite, react-swc, tailwindcss; port 5173; proxy `/api` → `localhost:8000`)
- [x] Create `frontend/tsconfig.json`, `tsconfig.app.json`, `tsconfig.node.json`
- [x] Create `frontend/components.json` (shadcn/ui config: dark theme, zinc base color, `@/` alias)
- [x] Create `frontend/index.html` (Vite SPA shell with `<div id="root">`)
- [x] Run `npm install` in `frontend/` and verify Vite dev server starts on port 5173
- [x] Create `src/styles/globals.css` (Tailwind v4 `@import` + `@theme` trading color tokens)
- [x] Create `src/lib/utils.ts` (`cn()` via clsx + tailwind-merge)
- [x] Create `src/lib/queryClient.ts` (TanStack Query QueryClient singleton)
- [x] Create `src/lib/formatters.ts` (port of `formatters.js`: formatDecimal, formatCurrency, formatPercentFromRatio, formatUtcTimestamp)
- [x] Create `src/store/apiStore.ts` (Zustand persist → localStorage key `ts_api_base_url`, with one-time migration from legacy `apiBaseUrl`)
- [x] Create API-key UI state for optional `X-API-Key` requests
- [x] Create `src/store/runsStore.ts` (Zustand persist → localStorage key `ts_backtest_runs`, max 100 runs)
- [x] Add shadcn/ui components: button, card, badge, input, label, select, table, textarea, dialog, toast

## Epic B - API Layer

- [x] Create `src/api/client.ts` (port of `client.js`: typed `ApiError` class, `requestJson<T>`, reads baseUrl from apiStore at call time, sends optional `X-API-Key`)
- [x] Create `src/api/dashboard.ts` (getDashboardStatus, getDashboardPositions, getDashboardEvents, postDashboardControl)
- [x] Create `src/api/backtests.ts` (createBacktestRun, getBacktestRun)
- [x] Create `src/api/analytics.ts` (getBacktestTradeAnalytics)
- [x] Create `src/api/patterns.ts` (trainPatterns, savePatternSet, listPatternSets, getPatternSet)
- [x] Create `src/api/strategies.ts` (createStrategyProfile, listStrategyProfiles, getStrategyProfile)

## Epic C - Layout and Router Shell

- [x] Create `src/main.tsx` (ReactDOM.createRoot, QueryClientProvider, RouterProvider)
- [x] Create `src/routes/__root.tsx` (AppShell: dark header with NavBar + `<Outlet />`)
- [x] Create `src/components/layout/NavBar.tsx` (links: Dashboard | Runs | Patterns | Strategies | New Run; active highlight via TanStack Router)
- [x] Create `src/components/shared/StatusBadge.tsx` (RUNNING=bull, PAUSED=warn, EMERGENCY=bear, INIT/UNKNOWN=muted)
- [x] Create `src/components/shared/StatTile.tsx` (label + value metric card)
- [x] Create `src/components/shared/ErrorBanner.tsx`
- [x] Create `src/components/shared/ApiSettingsBar.tsx` (single header widget replacing per-page API URL sections and preserving optional API Key input)

## Epic D - Dashboard Page

- [x] Create `src/hooks/useDashboardPolling.ts` (three `useQuery` calls, `refetchInterval: 5000`, `refetchIntervalInBackground: false`)
- [x] Create `src/components/dashboard/StatusCard.tsx` (state badge + heartbeat + uptime + LiveDot animation)
- [x] Create `src/components/dashboard/ControlButtons.tsx` (Pause/Resume/Reset; Reset uses shadcn Dialog; React 19 `startTransition`; `invalidateQueries(['dashboard'])` after action)
- [x] Create `src/components/dashboard/PositionsTable.tsx` (positions rows + cash row)
- [x] Create `src/components/dashboard/EventFeed.tsx` (severity-colored rows: INFO=info, WARNING=warn, ERROR/CRITICAL=bear)
- [x] Create `src/routes/dashboard.tsx`
- [ ] Verify legacy `apiBaseUrl` is migrated to `ts_api_base_url` (requires manual browser test)
- [ ] Verify optional API Key input is sent as `X-API-Key` (requires manual browser test)
- [ ] Verify dashboard polling behavior against a running backend (5s interval, control actions reflect immediately — requires live trading loop)

## Epic E - Run Detail Page

- [x] Create `src/components/charts/EquityCurveChart.tsx` (Recharts AreaChart, blue gradient, `equity_curve` data)
- [x] Create `src/components/charts/DrawdownChart.tsx` (Recharts AreaChart, red gradient, `drawdown_curve` data, y-axis inverted)
- [x] Create `src/components/charts/TradeScatterChart.tsx` (ScatterChart: PnL vs. entry time, green/red by win/loss — NEW)
- [x] Create `src/components/runs/RunSummaryGrid.tsx` (StatTile grid: return, maxDrawdown, volatility, winRate, started, finished)
- [x] Create `src/components/runs/SignalsTable.tsx` (strategy signal events using current DTO fields only: event, symbol, side, quantity, reason)
- [x] Create `src/components/runs/FillsTable.tsx` (fills + risk rejections using current DTO fields only: type, event, symbol, quantity, status)
- [x] Create `src/components/runs/TradesTable.tsx` (full trade list from analytics endpoint — NEW)
- [x] Create `src/routes/runs.$runId.tsx` (`staleTime` logic: `Infinity` for succeeded, `10_000` for running)
- [x] Verify Trade Analytics card renders from `GET /api/v1/analytics/backtests/{run_id}/trades` (trade_count:2, trades:2 confirmed)
- [x] Verify Run Detail renders correctly without timestamp fields in run events

## Epic F - Patterns Pages

- [x] Create `src/lib/patternParser.ts` (verbatim port of `parseExamples()` from `patternsPage.js`)
- [x] Create `src/components/patterns/PatternTrainForm.tsx` (two-step: POST `/patterns/train` preview → POST `/patterns` save; local `latestPreview` state)
- [x] Create `src/components/patterns/PatternPreviewTable.tsx` (use DTO field names consistent with backend, including `sample_size`)
- [x] Create `src/components/patterns/PatternSetsTable.tsx` (rows link to `/patterns/$patternSetId`)
- [x] Create `src/routes/patterns.tsx`
- [x] Create `src/routes/patterns.$patternSetId.tsx` (`staleTime: Infinity`)

## Epic G - Strategies and Runs List Pages

- [x] Create `src/lib/strategyParser.ts` (port of `parseMap()` from `strategiesPage.js`)
- [x] Create `src/components/strategies/StrategyForm.tsx` (key=value textareas; patternSet select from `useQuery`)
- [x] Create `src/components/strategies/StrategiesTable.tsx`
- [x] Create `src/routes/strategies.tsx`
- [x] Create `src/hooks/useRunsList.ts` — logic inlined directly in `runs.tsx` (useQueries batch refresh + updateRunStatus); separate hook not required
- [x] Create `src/components/runs/RunsTable.tsx` — rendered inline in `runs.tsx`
- [x] Create `src/routes/runs.tsx`

## Epic H - Create Run Page

- [x] Create `src/routes/index.tsx` (backtest form; `runsStore.saveRun()` → navigate to `/runs/$runId` on success; `starting_cash` field added after backend verification)
- [x] Strategy profile select populated via `useQuery(listStrategyProfiles)` with `staleTime: 30_000`

## Epic I - Cleanup and Documentation

- [x] Remove old vanilla HTML files: `dashboard.html`, `patterns.html`, `strategies.html`, `runs.html`, `run.html`, `pattern.html`, `index.old.html`
- [x] Remove old `frontend/src/pages/`, `frontend/src/api/client.js`, `frontend/src/utils/`, `frontend/src/state/`, `frontend/src/styles.css`
- [x] Add `frontend/node_modules/` and `frontend/dist/` to `.gitignore`
- [ ] Commit `frontend/routeTree.gen.ts` (TanStack Router codegen output — must be committed)
- [x] Update `README.md` frontend section: replace `python -m http.server 5173 -d frontend` with `cd frontend && npm install && npm run dev`
- [x] Update `GEMINI.md` with the same frontend dev instruction change

## Epic J - Verification

- [x] `npm run dev` starts without errors on port 5173
- [x] All 7 routes created and wired: `/`, `/dashboard`, `/runs`, `/runs/$runId`, `/patterns`, `/patterns/$patternSetId`, `/strategies`
- [x] `npm run build` completes without TypeScript errors (`tsc -b` clean, vite build 2465 modules)
- [x] POST /backtests → run_id returned, status succeeded
- [x] GET /backtests/{id} → summary, equity_curve, drawdown_curve, signals, orders, risk_rejections
- [x] GET /analytics/backtests/{id}/trades → trade_count and trades list confirmed
- [x] GET /patterns, GET /patterns/{id} → list and detail confirmed
- [x] GET /strategies → list confirmed
- [x] GET /dashboard/* → correct responses (no live loop → detail message as expected)
- [ ] Dashboard polls every 5 seconds; Pause/Resume/Reset controls work (requires live trading loop)
- [ ] Dashboard preserves API Key workflow for protected deployments (requires manual browser test)
- [ ] Legacy `apiBaseUrl` is migrated automatically (requires manual browser test)
- [ ] Patterns: train preview, save, navigate to detail page (requires manual browser test)
- [ ] Create Run: form submits, navigates to run detail (requires manual browser test)
- [ ] `ts_backtest_runs` backward compatibility (requires manual browser test)
- [ ] Dark mode renders correctly in Chrome and Firefox (requires manual browser test)
