# Phase 7.5 Implementation Plan

관련 문서:
- PRD: `prd/phase_7_5_prd.md`
- 실행 추적: `prd/phase_7_5_task.md`
- Phase 7 구현 계획 참조: `prd/phase_7_implementation_plan.md`

## Goal

Phase 7.5는 Phase 7 완료 승인을 위한 세 가지 잔여 항목을 닫는다.

1. **Playwright e2e smoke test 하네스** — `npm run test:e2e`로 3개 smoke test 통과
2. **Dashboard portfolio equity chart** — placeholder → 실제 Recharts 차트
3. **`/runs/[runId]` 탭 기반 레이아웃** — 카드 나열 → 4탭 구조

가장 중요한 구현 원칙:
- 백엔드 API를 변경하지 않는다. 기존 polling 응답에서 필요한 데이터를 파생한다.
- 기존 차트/테이블 컴포넌트의 내부 로직을 변경하지 않는다. 레이아웃과 조합만 변경한다.
- 각 Slice는 독립적으로 검증 가능하다. Slice A → B → C 순서로 진행한다.

## Review Status (2026-04-07, Codex → Claude 보정)

- [x] Step 7.5-A1. Playwright 의존성 설치 및 기본 설정 — `page.route()` 기반 mock 채택 (MSW browser mode 미사용)
- [x] Step 7.5-A2. Playwright route 기반 API mock 핸들러 작성
- [x] Step 7.5-A3. Smoke test 3개 작성 및 통과
- [x] Step 7.5-B1. Dashboard API 응답 구조 확인 — **Go 판정**: `cash + Σ(qty × avg_cost + unrealized_pnl)` 파생 공식 확정
- [x] Step 7.5-B2. EquityChart 컴포넌트 구현
- [x] Step 7.5-B3. Dashboard page placeholder 교체
- [x] Step 7.5-C1. Tabs UI 컴포넌트 인터페이스 적합성 확인
- [x] Step 7.5-C2. RunDetailTabs 컴포넌트 구현 — Charts 탭 중복 제거, analytics 독립/의존 컴포넌트 분리
- [x] Step 7.5-C3. `/runs/[runId]/page.tsx` 탭 레이아웃 전환
- [x] Step 7.5-D. 최종 검증 — tsc/lint/build/e2e 4개 PASS

체크 기준:
- `[x]`는 구현 완료 및 자동화 검증(tsc/lint/build/e2e) 통과가 확인된 항목.
- Codex 리뷰에서 `[ ]`였던 A1/A2/B1/C2/D는 설계 변경 사유와 함께 보정 완료.

## Preconditions

- `frontend/` 기준: Next.js 16, TypeScript 5, TanStack Query v5, Recharts v3, react-hook-form + zod
- `tsc --noEmit` PASS, `npm run lint` PASS, `next build` PASS (Phase 7 완료 상태)
- `@base-ui/react` 설치됨 (`package.json` 확인)
- `frontend/components/ui/tabs.tsx` 존재 확인됨 (Base UI 래퍼, `Tabs`/`TabsList`/`TabsTrigger`/`TabsContent` export). Step 7.5-C에서 재사용한다.

## Locked Design Decisions

### 1. Playwright `page.route()` 기반 API mock을 사용한다

~~MSW browser mode~~ → Playwright 네이티브 `page.route()` interception으로 변경.
변경 사유: MSW Service Worker의 `worker.start()`가 비동기라 초기 fetch를 놓칠 수 있음 (race condition).
`page.route()`는 페이지 로드 전에 등록되므로 race-free.

```
e2e/
├── smoke.spec.ts           ← Playwright test 파일
└── mocks/
    ├── handlers.ts         ← Playwright page.route() 기반 fixture + mock 등록
    └── setup.ts            ← setupMockRoutes re-export
```

`playwright.config.ts`는 `next build + next start` 결과물을 타겟으로 한다.
MSW는 devDependency로 유지하되 browser mode(mockServiceWorker.js)는 사용하지 않는다.

### 2. Dashboard equity chart 데이터 전략

기존 `getDashboardPositions()` 응답에서 portfolio equity를 직접 노출하지 않는 경우:
- 클라이언트에서 polling 응답을 받을 때마다 `totalValue` 값을 누적하여 시계열을 구성한다.
- 누적 시계열은 `useRef` (mutable accumulation) + `useMemo` (snapshot on `positionsQuery.dataUpdatedAt` 변경) 패턴으로 관리한다. React 19의 `react-hooks/set-state-in-effect` 및 `react-hooks/refs` ESLint 규칙을 준수하기 위해 `useState`+`useEffect` 대신 이 패턴을 채택했다.
- 5초 throttle로 중복 기록을 방지하고, 최대 300 데이터포인트를 유지한다.
- 이 방식은 페이지 새로고침 시 데이터가 초기화되는 한계가 있으나, Phase 7.5 범위에서는 허용한다.

실제 API 응답에 equity 시계열 필드가 있다면 그것을 우선 사용한다.

### 3. `/runs/[runId]` 탭 구성

탭 4개:

| 탭 ID | 표시 이름 | 포함 컴포넌트 |
|---|---|---|
| `summary` | Summary | `RunSummaryGrid`, `StatTile` 그리드 (analytics) |
| `charts` | Charts | `EquityCurveChart`, `DrawdownChart`, `TradeScatterChart` |
| `trades` | Trades | `TradesTable`, `FillsTable` |
| `signals` | Signals | `SignalsTable` |

탭은 `components/runs/RunDetailTabs.tsx`로 분리한다. `page.tsx`는 데이터 페칭만 담당하고 렌더링을 `RunDetailTabs`에 위임한다.

## Contract Deltas

### package.json 추가 의존성
- `@playwright/test` (devDependencies)
- `msw` (devDependencies)

### package.json 추가 스크립트
```json
"test:e2e": "playwright test"
```

### 신규 파일
- `frontend/playwright.config.ts`
- `frontend/e2e/smoke.spec.ts`
- `frontend/e2e/mocks/handlers.ts`
- `frontend/e2e/mocks/setup.ts`
- `frontend/components/dashboard/EquityChart.tsx`
- `frontend/components/runs/RunDetailTabs.tsx`
- ~~`frontend/components/ui/tabs.tsx`~~ (이미 존재 확인됨, 신규 생성 불필요)

### 수정 파일
- `frontend/app/dashboard/page.tsx`
- `frontend/app/runs/[runId]/page.tsx`

## Implementation Steps

---

### Step 7.5-A1. Playwright 의존성 설치 및 기본 설정

**목적**: e2e 테스트 환경 기반을 구성한다.

**작업**:
1. Playwright 설치
   ```bash
   cd frontend && npm install -D @playwright/test msw
   npx playwright install chromium
   ```
   msw는 향후 unit/integration test Node adapter 용도로 함께 설치한다. browser mode(mockServiceWorker.js)는 사용하지 않는다.
2. `frontend/playwright.config.ts` 생성:
   - `webServer`: `npm run build && npm start`
   - `baseURL`: `http://localhost:3000`
   - `headless`: `true`
   - `testDir`: `./e2e`
3. `tsconfig.json`에 `"e2e"` exclude 추가 (앱 빌드와 e2e 타입 분리)
4. `eslint.config.mjs`에 `"e2e/**"`, `"test-results/**"` ignore 추가

**파일**:
- `frontend/package.json`
- `frontend/playwright.config.ts`
- `frontend/tsconfig.json`
- `frontend/eslint.config.mjs`

**Exit criteria**: `npx playwright test --list`가 실행 가능하다.

---

### Step 7.5-A2. Playwright route 기반 API mock 핸들러 작성

**목적**: smoke test가 실 백엔드 없이 동작할 수 있도록 핵심 API를 mock한다.

**작업**:
1. `frontend/e2e/mocks/handlers.ts` 작성 — Playwright `page.route()` 기반:
   - `GET /api/v1/dashboard/status` → fixture 응답
   - `GET /api/v1/dashboard/positions` → fixture 응답
   - `GET /api/v1/dashboard/events` → fixture 응답
   - `GET /api/v1/backtests/:runId` → fixture 응답 (단일 실행 상세)
   - `GET /api/v1/analytics/backtests/:runId/trades` → fixture 응답
   - `GET /api/v1/strategies` → fixture 응답
   - 참고: `/runs` 목록 페이지는 `runsStore`(localStorage) 기반이므로 목록 API mock은 불필요.
2. `frontend/e2e/mocks/setup.ts` 작성:
   - `setupMockRoutes` re-export

**파일**:
- `frontend/e2e/mocks/handlers.ts`
- `frontend/e2e/mocks/setup.ts`

**Exit criteria**: handlers.ts가 TypeScript 오류 없이 동작한다 (e2e는 tsconfig exclude이므로 Playwright 실행으로 검증).

---

### Step 7.5-A3. Smoke test 3개 작성 및 통과

**목적**: Phase 7.5 완료 기준인 smoke test 3개를 작성하고 통과한다.

**작업**:
1. `frontend/e2e/smoke.spec.ts` 작성:
   ```
   test 1: 홈 페이지(/) 로드 → 네비게이션 링크 존재 확인
   test 2: 대시보드(/dashboard) 로드 → MetricCard 컨테이너 존재 확인
   test 3: 백테스트 상세(/runs/[runId]) 로드 → 상세 컨테이너 렌더링 확인
   ```
   참고: `/runs` 목록은 localStorage 기반 `runsStore`에 의존하므로, test 3는 deterministic한 `/runs/[runId]` 상세 페이지를 대상으로 한다. `page.route()`로 `GET /api/v1/backtests/:runId`를 mock하여 fixture 데이터를 반환한다.
2. 각 test의 `beforeEach`에서 `page.addInitScript(() => localStorage.clear())`로 state isolation 보장
3. `setupMockRoutes(page)`로 API mock 등록 후 페이지 이동
3. `npm run test:e2e` 실행하여 3개 통과 확인

**파일**:
- `frontend/e2e/smoke.spec.ts`

**Exit criteria**: `npm run test:e2e`로 3개 smoke test PASS.

---

### Step 7.5-B1. Dashboard API 응답 구조 확인 (Go/No-Go Gate)

**목적**: `getDashboardStatus` / `getDashboardPositions` 응답에서 equity 파생 가능 여부를 확인하고, B2/B3 진행 여부를 결정한다.

**배경**: 현재 `DashboardStatus`/`PositionsResponse` 타입에는 `totalValue`/`equity`/`portfolio_value` 시계열 필드가 존재하지 않는 것으로 확인되었다. 클라이언트 누적 방식은 페이지 새로고침 시 초기화되는 한계가 있으므로, 이 방식의 신뢰성을 평가해야 한다.

**작업**:
1. `frontend/lib/api/dashboard.ts`와 `frontend/lib/api/types.ts`에서 응답 타입 확인
2. `DashboardStatus` 또는 `PositionsResponse`에 equity 파생 가능 필드 유무 파악
3. **Go/No-Go 판정**:
   - **Go**: 응답에 `total_value` 등 필드가 있거나, `positions[].quantity * price + cash` 등으로 신뢰 가능한 파생 공식을 문서화할 수 있는 경우 → B2/B3 진행
   - **No-Go**: 신뢰 가능한 파생 공식이 없는 경우 → B2/B3를 보류하고 Epic B를 Phase 8로 이동

**파일**:
- `frontend/lib/api/types.ts` (read-only)
- `frontend/lib/api/dashboard.ts` (read-only)

**Exit criteria**: Go/No-Go 판정이 내려지고, Go인 경우 equity 파생 공식이 문서화된다.

---

### Step 7.5-B2. EquityChart 컴포넌트 구현

**목적**: dashboard에 표시할 portfolio equity Recharts 차트를 구현한다.

**작업**:
1. `frontend/components/dashboard/EquityChart.tsx` 생성:
   - props: `data: Array<{ time: number; value: number }>`, `loading: boolean`
   - Recharts `AreaChart` (또는 `LineChart`)로 렌더링
   - `ChartContainer`로 감싸서 loading/empty 상태 처리
   - `'use client'` 적용
2. Step 7.5-B1에서 확정한 전략에 따라 데이터 파생 로직 결정:
   - API 응답에 필드 있음: 직접 사용
   - 없음: `useDashboardPolling`에 `equitySeries` 누적 로직 추가

**파일**:
- `frontend/components/dashboard/EquityChart.tsx`
- `frontend/hooks/useDashboardPolling.ts` (누적 방식 선택 시 수정)

**Exit criteria**: `EquityChart`가 sample data로 렌더링된다. `tsc --noEmit` PASS.

---

### Step 7.5-B3. Dashboard page placeholder 교체

**목적**: `dashboard/page.tsx`의 `ChartContainer empty={true}` placeholder를 `EquityChart`로 교체한다.

**작업**:
1. `frontend/app/dashboard/page.tsx` 수정:
   - `EquityChart` import 추가
   - `empty={true}` + `{null}` 블록을 `EquityChart` 렌더링으로 교체
   - 데이터 없는 경우 `EquityChart`의 `ChartContainer empty` 상태가 처리
2. `next build` 통과 확인

**파일**:
- `frontend/app/dashboard/page.tsx`

**Exit criteria**: `next build` PASS. 대시보드 페이지에 `empty={true}` placeholder가 제거됨.

---

### Step 7.5-C1. Tabs UI 컴포넌트 인터페이스 적합성 확인

**목적**: 기존 `frontend/components/ui/tabs.tsx`가 `RunDetailTabs`에 필요한 인터페이스를 제공하는지 확인한다.

**배경**: `tabs.tsx`는 이미 존재하며 Base UI `@base-ui/react/tabs` 래퍼로 `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent`를 export한다. 신규 작성은 불필요하다.

**작업**:
1. `frontend/components/ui/tabs.tsx`의 export 인터페이스 확인 (완료됨: `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent`, `tabsListVariants`)
2. `RunDetailTabs`에서 사용할 props 패턴과의 호환성 확인 (value/defaultValue, orientation 등)
3. 비호환 시에만 경량 수정 (fallback note)

**파일**:
- `frontend/components/ui/tabs.tsx` (read-only, 수정 필요 시에만)

**Exit criteria**: `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent`가 `RunDetailTabs`에 필요한 인터페이스를 제공함이 확인된다.

---

### Step 7.5-C2. RunDetailTabs 컴포넌트 구현

**목적**: 기존 컴포넌트를 4탭으로 재조합하는 `RunDetailTabs`를 구현한다.

**작업**:
1. `frontend/components/runs/RunDetailTabs.tsx` 생성:
   - props: `run: BacktestRunDTO`, `analytics: TradeAnalyticsDTO | undefined`
   - 4개 탭 구성 (Summary, Charts, Trades, Signals)
   - 기존 컴포넌트를 탭 내부에 그대로 배치
   - `'use client'` 적용
   - **analytics unavailable 처리**: `analytics`가 `undefined`인 경우 analytics-의존 컴포넌트(StatTile, TradeScatterChart, TradesTable)만 안내 메시지로 대체. result 기반 컴포넌트(RunSummaryGrid, EquityCurveChart, DrawdownChart, FillsTable, SignalsTable)는 항상 렌더. 탭 자체는 비활성화하지 않는다.
2. 탭 간 전환 시 불필요한 re-fetch가 없도록 탭 상태는 URL query param `?tab=summary` 방식이 아닌 로컬 상태로 관리

**파일**:
- `frontend/components/runs/RunDetailTabs.tsx`

**Exit criteria**: `RunDetailTabs`가 TypeScript 오류 없이 컴파일된다.

---

### Step 7.5-C3. `/runs/[runId]/page.tsx` 탭 레이아웃 전환

**목적**: page.tsx를 데이터 페칭만 담당하도록 단순화하고, 렌더링을 `RunDetailTabs`에 위임한다.

**작업**:
1. `frontend/app/runs/[runId]/page.tsx` 수정:
   - 기존 카드 나열 JSX를 제거
   - `RunDetailTabs` import 및 렌더링으로 교체
   - 데이터 페칭 로직(`useQuery`)은 유지
2. `run.result` 없는 경우 처리 유지

**파일**:
- `frontend/app/runs/[runId]/page.tsx`

**Exit criteria**: `next build` PASS. `/runs/[runId]` 페이지에서 탭이 렌더링됨.

---

### Step 7.5-D. 최종 검증

**목적**: Phase 7.5 완료 기준을 모두 충족하는지 확인한다.

**작업**:
1. `npx tsc --noEmit` → 0 errors
2. `npm run lint` → 0 errors, 0 warnings
3. `npm run build` → next build PASS
4. `npm run test:e2e` → smoke test 3개 PASS
5. 수동 확인:
   - 대시보드 equity chart 영역에 차트가 렌더링됨 (또는 데이터 없음 시 empty 상태)
   - `/runs/[runId]` 페이지에서 Summary / Charts / Trades / Signals 탭 전환 동작

**Exit criteria**: 4개 자동화 검증 모두 PASS. Phase 7.5 완료 승인 가능.

---

## Validation Matrix

| 항목 | 방법 | 기준 |
|---|---|---|
| TypeScript 타입 | `tsc --noEmit` | 0 errors |
| ESLint | `npm run lint` | 0 errors, 0 warnings |
| Next.js 빌드 | `npm run build` | 에러 없이 완료 |
| Smoke test | `npm run test:e2e` | 3개 PASS |
| Dashboard chart | 수동 확인 | placeholder 제거, 차트 또는 empty 상태 표시 |
| Runs 탭 레이아웃 | 수동 확인 | 4탭 전환 동작 |

## PR Slices

- **PR A**: `Step 7.5-A1 ~ A3` — Playwright e2e 하네스 + smoke test
- **PR B**: `Step 7.5-B1 ~ B3` — Dashboard equity chart
- **PR C**: `Step 7.5-C1 ~ C3` — Runs 탭 레이아웃
- **PR D**: 최종 검증은 별도 PR 없이 각 PR 내에서 확인

## Risks and Fallbacks

| 리스크 | 가능성 | 대응 |
|---|---|---|
| ~~MSW Service Worker registration race로 첫 fetch 누락~~ | — | Playwright `page.route()` 채택으로 리스크 해소. MSW browser mode 미사용. |
| Dashboard API 응답에 equity 시계열 데이터 없음 | 중 | **Step B1을 go/no-go gate로 운영**. 신뢰 가능한 파생 공식이 문서화되지 않으면 B2/B3를 보류하고 Phase 8로 이동. 클라이언트 누적은 go 판정 시에만 진행. |
| ~~Base UI Tabs 없어서 구현 비용 증가~~ | — | `tabs.tsx` 이미 존재 확인됨. 리스크 해소. |
| `next build` 시 Playwright 관련 import 오류 | 저 | `e2e/` 디렉토리를 `tsconfig.json`의 `exclude`에 추가 |
| `/runs` smoke test가 localStorage 상태에 의존 | 중 | smoke test 대상을 `/runs/[runId]` 상세 페이지로 변경하여 `runsStore` 의존성 제거. `page.route()`로 `GET /api/v1/backtests/:runId`만 mock. |
| `ApiSettingsBar` persisted state가 test를 오염 | 저 | 각 test에서 localStorage를 초기화하거나, Playwright context isolation(새 브라우저 컨텍스트)으로 격리 |
