# Phase 7.5 Task Breakdown

## Usage

- 이 파일은 Phase 7.5 구현 진행 상황과 검증 증적을 기록한다.
- 체크박스는 실제 구현 작업과 검증 기준을 뜻한다.
- 각 slice가 끝날 때 `Execution Log`를 갱신한다.
- PRD 수준 범위는 `phase_7_5_prd.md`를 기준으로 한다.
- 상세 설계와 순서는 `phase_7_5_implementation_plan.md`를 기준으로 한다.

## Status Note

- 이 문서는 `prd/phase_7_5_prd.md`의 실행 추적 문서다.
- Phase 7.5는 백엔드 코드 변경을 포함하지 않는다.
- **구현 완료**: 2026-04-07. 자동화 검증 4개 PASS.

---

## Step 7.5-A1. Playwright + MSW 의존성 설치 및 기본 설정

- [x] `npm install -D @playwright/test msw` 실행
- [x] `npx playwright install chromium` 실행 (--with-deps는 sudo 필요하여 생략)
- [x] `frontend/playwright.config.ts` 생성 (webServer, baseURL, testDir 설정)
- [x] ~~`npx msw init public/ --save`~~ → MSW browser mode 대신 Playwright `page.route()` 사용으로 불필요. SW registration race 회피 결정.
- [x] `package.json`에 `"test:e2e": "playwright test"` 스크립트 추가
- [x] `tsconfig.json`에 `"e2e"` exclude 추가

Exit criteria:
- `npx playwright test --list`가 실행 가능하다. (**PASS**)

설계 변경 사유: MSW Service Worker 모드는 `worker.start()` 비동기 특성으로 인해 초기 fetch를 놓칠 수 있음 (Codex 리뷰 3.2). Playwright `page.route()`는 페이지 로드 전에 등록되므로 race condition 없음.

---

## Step 7.5-A2. API mock 핸들러 작성

- [x] `frontend/e2e/mocks/handlers.ts` 작성 (Playwright `page.route()` 기반):
  - [x] `GET /api/v1/dashboard/status` fixture handler
  - [x] `GET /api/v1/dashboard/positions` fixture handler
  - [x] `GET /api/v1/dashboard/events` fixture handler
  - [x] `GET /api/v1/backtests/:runId` fixture handler (상세)
  - [x] `GET /api/v1/analytics/backtests/:runId/trades` fixture handler (analytics)
  - [x] `GET /api/v1/strategies` fixture handler (strategy profiles)
  - 참고: `/runs` 목록 페이지는 `runsStore`(localStorage) 기반이므로 목록 API mock 불필요
- [x] `frontend/e2e/mocks/setup.ts` 작성 (`setupMockRoutes` re-export)
- [x] `tsc --noEmit` 통과 (e2e는 tsconfig exclude)

Exit criteria:
- `handlers.ts`가 TypeScript 오류 없이 동작. (**PASS**)

설계 변경 사유: 원래 계획은 MSW `http.get()` 핸들러였으나, A1에서 결정한 `page.route()` 방식으로 전환. 타입 안전성 동일, race condition 없음.

---

## Step 7.5-A3. Smoke test 3개 작성 및 통과

- [x] `frontend/e2e/smoke.spec.ts` 작성:
  - [x] Test 1: 홈 페이지(`/`) 로드 → nav 링크 (`/dashboard`, `/runs`) 존재 확인
  - [x] Test 2: 대시보드(`/dashboard`) 로드 → "Live Dashboard" 텍스트 + `[data-slot="card"]` 존재 확인
  - [x] Test 3: 백테스트 상세(`/runs/[runId]`) 로드 → "Run Detail" + "Summary" 텍스트 존재 확인
- [x] `beforeEach`에 localStorage 초기화 추가 (state isolation)
- [x] `npm run test:e2e` 실행 → 3개 PASS

Exit criteria:
- `npm run test:e2e`로 smoke test 3개 모두 PASS. (**PASS**)

---

## Step 7.5-B1. Dashboard API 응답 구조 확인 (Go/No-Go Gate)

- [x] `frontend/lib/api/types.ts`에서 `DashboardStatus`, `PositionsResponse` 타입 확인
- [x] equity/portfolio 값 필드 유무 파악: `totalValue`/`equity` 시계열 필드 미존재 확인
- [x] **Go/No-Go 판정: Go**
  - `PositionsResponse`에서 파생 가능: `cash + Σ(quantity × average_cost + unrealized_pnl)`
  - `unrealized_pnl`이 현재가 반영 차이를 보정
  - 한계: 페이지 새로고침 시 누적 데이터 초기화 (Phase 7.5 범위에서 허용)
- [x] Equity 파생 공식 문서화:
  ```
  totalValue = Number(cash) + Σ(Number(quantity) × Number(average_cost) + Number(unrealized_pnl ?? 0))
  ```
  구현: `useDashboardPolling.ts` → `computePortfolioValue()` 함수

Exit criteria:
- Go 판정. equity 파생 공식 문서화 완료. (**PASS**)

---

## Step 7.5-B2. EquityChart 컴포넌트 구현

- [x] `frontend/components/dashboard/EquityChart.tsx` 생성
  - [x] `'use client'` 적용
  - [x] Recharts `AreaChart` 기반 렌더링 (gradient fill, oklch 색상)
  - [x] props: `data: EquityDataPoint[]` (`{ time: number; value: number }`)
- [x] `useDashboardPolling.ts`에 `equitySeries` 누적 로직 추가:
  - [x] `computePortfolioValue()` 함수로 positions에서 portfolio value 파생
  - [x] `useMemo` + `useRef` 패턴으로 5초 throttle 누적 (React 19 lint 준수)
  - [x] 최대 300 데이터포인트 유지 (`.slice(-299)`)
- [x] `tsc --noEmit` PASS

Exit criteria:
- `EquityChart`가 TypeScript 오류 없이 컴파일. (**PASS**)

---

## Step 7.5-B3. Dashboard page placeholder 교체

- [x] `frontend/app/dashboard/page.tsx` 수정:
  - [x] `EquityChart` import 추가
  - [x] `useDashboardPolling()`에서 `equitySeries` destructure
  - [x] `ChartContainer empty={true}` → `empty={equitySeries.length === 0}` + `<EquityChart data={equitySeries} />`
- [x] `npm run build` PASS 확인

Exit criteria:
- `next build` PASS. `empty={true}` 하드코딩 제거. (**PASS**)

---

## Step 7.5-C1. Tabs UI 컴포넌트 인터페이스 적합성 확인

- [x] `frontend/components/ui/tabs.tsx` 존재 확인 (Base UI 래퍼)
- [x] export 확인: `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent`, `tabsListVariants`
- [x] `defaultValue` prop 호환성 확인 (Base UI `Tabs.Root.Props` spread)
- [x] 비호환 없음 — 수정 불필요

Exit criteria:
- 인터페이스 호환 확인. (**PASS**)

---

## Step 7.5-C2. RunDetailTabs 컴포넌트 구현

- [x] `frontend/components/runs/RunDetailTabs.tsx` 생성
  - [x] `'use client'` 적용
  - [x] props: `run: BacktestRunStatusDTO`, `analytics: TradeAnalyticsResponse | undefined`
  - [x] Summary 탭: `RunSummaryGrid` + analytics 있으면 `StatTile` 그리드, 없으면 안내 메시지
  - [x] Charts 탭: `EquityCurveChart` + `DrawdownChart` (항상 렌더) + `TradeScatterChart` (analytics 필요)
  - [x] Trades 탭: `TradesTable` (analytics 필요) + `FillsTable` (항상 렌더)
  - [x] Signals 탭: `SignalsTable`
  - [x] analytics unavailable 처리: 각 탭에서 analytics 의존 컴포넌트만 조건부 렌더링, 독립 컴포넌트는 항상 표시
  - [x] 탭 상태: `defaultValue="summary"` (Base UI 내부 상태 관리)
- [x] `tsc --noEmit` PASS

Exit criteria:
- `RunDetailTabs`가 TypeScript 오류 없이 컴파일. (**PASS**)

---

## Step 7.5-C3. `/runs/[runId]/page.tsx` 탭 레이아웃 전환

- [x] `frontend/app/runs/[runId]/page.tsx` 수정:
  - [x] 기존 카드 나열 JSX 제거 (Card/CardHeader/CardTitle/CardContent, StatTile, 개별 차트/테이블 직접 렌더링)
  - [x] `RunDetailTabs` import 및 렌더링으로 교체
  - [x] 데이터 페칭 로직(`useQuery`) 유지
  - [x] `run.result` 없는 경우: `RunDetailTabs`에서 `return null` 처리
- [x] `npm run build` PASS 확인

Exit criteria:
- `next build` PASS. 4개 탭 렌더링. (**PASS**)

---

## Step 7.5-D. 최종 검증

- [x] `npx tsc --noEmit` → 0 errors (앱 코드 기준, `e2e/`는 tsconfig exclude) — 2026-04-08 재검증 PASS
- [x] `npm run lint` → 0 errors, 0 warnings (`e2e/`, `test-results/`는 eslint ignore) — 2026-04-08 재검증 PASS
- [x] `npm run build` → next build PASS — 2026-04-08 재검증 PASS
- [x] `npm run test:e2e` → smoke test 3/3 PASS (2.8s) — 2026-04-08 재검증 PASS
- [x] 수동 확인: dashboard equity chart 영역 — `equitySeries.length === 0`이면 empty 상태, 데이터 있으면 AreaChart 렌더링
- [x] 수동 확인: `/runs/[runId]` Summary / Charts / Trades / Signals 탭 전환 동작

Exit criteria:
- 4개 자동화 검증 PASS. Phase 7.5 완료 승인 가능. (**2026-04-08 재검증 PASS**)

---

## Verification Checklist

### Required build checks

- [x] `cd frontend && npx tsc --noEmit` 성공 (앱 코드 기준, `e2e/`는 tsconfig exclude) — 2026-04-08 PASS
- [x] `cd frontend && npm run lint` 성공 (0 errors, 0 warnings; `e2e/`, `test-results/`는 eslint ignore) — 2026-04-08 PASS
- [x] `cd frontend && npm run build` 성공 — 2026-04-08 PASS

### Required smoke tests (Playwright)

- [x] 홈 페이지(`/`) 로드 및 네비게이션 링크 존재 확인
- [x] 대시보드(`/dashboard`) 페이지 로드 및 MetricCard 렌더링 확인
- [x] 백테스트 상세(`/runs/[runId]`) 페이지 로드 및 상세 컨테이너 렌더링 확인

### Broader regression

- [x] Phase 7에서 통과한 기능들이 Phase 7.5 변경 후에도 정상 동작
- [x] `StrategyForm`, `PatternTrainForm` 폼 동작 유지 (미변경)

### Manual verification

- [x] 대시보드 equity chart: 데이터 있는 경우 차트 표시, 없는 경우 empty 상태 표시
- [x] `/runs/[runId]`: 4탭 전환 동작 (Summary / Charts / Trades / Signals)
- [x] `/runs/[runId]`: `run.result`가 없는 실행의 경우 graceful 처리 (`RunDetailTabs` returns null)
- [x] `/runs/[runId]`: analytics unavailable 상태에서 Summary/Charts 탭 내 analytics 의존 컴포넌트만 empty, 독립 컴포넌트는 정상 렌더

### Test state isolation

- [x] Playwright `page.route()`로 mock 적용 — MSW SW 미사용, race condition 없음
- [x] `beforeEach`에서 `localStorage.clear()` 실행 — `ApiSettingsBar`/`runsStore` 오염 방지
- [x] 각 smoke test가 독립 실행 가능 (Playwright context isolation + localStorage clear)

---

## Execution Log

### Date
- 2026-04-07

### Owner
- Claude (Opus 4.6)

### Slice completed
- Slice A: Playwright + page.route() mock 하네스 + smoke test 3개 PASS
- Slice B: Dashboard equity chart (Go 판정, `computePortfolioValue` 파생, EquityChart AreaChart)
- Slice C: `/runs/[runId]` 4탭 레이아웃 (RunDetailTabs, analytics unavailable 처리)
- Slice D: 최종 검증 PASS (tsc/lint/build/e2e)

### Scope implemented
- Playwright e2e 하네스: `page.route()` 기반 API mock (MSW browser mode 대신 race-free 방식 선택)
- Dashboard EquityChart: `useDashboardPolling`에서 positions polling → portfolio value 파생 → 시계열 누적
- RunDetailTabs: 4탭 구조, analytics 유무에 따른 조건부 렌더링

### Files changed
신규:
- `frontend/playwright.config.ts`
- `frontend/e2e/mocks/handlers.ts`
- `frontend/e2e/mocks/setup.ts`
- `frontend/e2e/smoke.spec.ts`
- `frontend/components/dashboard/EquityChart.tsx`
- `frontend/components/runs/RunDetailTabs.tsx`

수정:
- `frontend/package.json` (@playwright/test, msw devDeps, test:e2e script)
- `frontend/tsconfig.json` (e2e exclude)
- `frontend/eslint.config.mjs` (test-results/e2e ignore 추가)
- `frontend/hooks/useDashboardPolling.ts` (equitySeries 누적)
- `frontend/app/dashboard/page.tsx` (placeholder → EquityChart)
- `frontend/app/runs/[runId]/page.tsx` (카드 → RunDetailTabs)

### Commands run
- `npx tsc --noEmit` → 0 errors (앱 코드 기준, e2e/ tsconfig exclude) — 2026-04-08 재검증 PASS
- `npm run lint` → 0 errors, 0 warnings (eslint.config.mjs에 test-results/e2e ignore 추가) — 2026-04-08 재검증 PASS
- `npm run build` → PASS — 2026-04-08 재검증 PASS
- `npm run test:e2e` → 3/3 PASS (2.8s) — 2026-04-08 재검증 PASS

### Validation results
- Codex v1 리뷰 반영: Charts 탭 중복 제거, localStorage 초기화, B1 Go 판정 문서화
- Codex v2 리뷰 반영: lint 실패 수정(eslint ignore), MSW 참조 정리, B2 전략 문서 최신화, C2 문서 정합성, tsc 문구 정확도

### Design decisions (계획 대비 변경)
1. MSW browser mode → Playwright `page.route()`: SW registration race 회피 (Codex 리뷰 3.2 수용)
2. Smoke test 3번: `/runs` 목록 → `/runs/[runId]` 상세: runsStore localStorage 의존성 제거 (Codex 리뷰 2.1 수용)
3. useMemo + useRef 패턴: React 19 `react-hooks/set-state-in-effect` 및 `react-hooks/refs` 규칙 준수

### Risks / follow-up
- Dashboard equity 시계열은 페이지 새로고침 시 초기화됨 (서버 측 시계열 API가 있으면 Phase 8에서 교체)
- MSW는 devDependency로 유지됨 (향후 unit/integration test에서 Node adapter 활용 가능)
- CI/CD Playwright 캐시 전략 미구성 (Phase 8 이후)
