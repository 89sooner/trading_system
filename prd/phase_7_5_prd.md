# Phase 7.5 PRD

관련 문서:
- 이전 phase 범위/결과: `prd/phase_7_prd.md`
- Phase 7 완료 검토: `prd/phase_7_review_from_codex.md`
- 상세 구현 계획: `prd/phase_7_5_implementation_plan.md`
- 실행 추적: `prd/phase_7_5_task.md`
- Phase 7 실행 증적: `prd/phase_7_task.md`

## 문서 목적

이 문서는 Phase 7(Next.js App Router 전환)에서 완료 승인을 받지 못한 세 가지 잔여 항목을 닫는 `Phase 7.5` 범위를 정의한다.

Phase 7.5는 새로운 기능 추가가 아니라 **Phase 7 완료 기준 충족**을 목적으로 한다. Phase 7 PRD의 PR-5, PR-8이 남긴 미완 항목을 정확히 겨냥하며, 범위를 그 이상으로 확장하지 않는다.

## Goal

1. Playwright e2e smoke test 하네스를 구축하여 PR-8 완료 기준을 충족한다.
2. 대시보드 portfolio equity chart placeholder를 실제 차트로 교체하여 PR-4 완료 기준을 충족한다.
3. `/runs/[runId]` 상세 페이지를 탭 기반 레이아웃으로 전환하여 PR-5 UX 명세를 충족한다.

## Current Baseline

- 프론트엔드: `frontend/` — Next.js 16, App Router, TypeScript, Tailwind CSS v4
- 데이터 페칭: TanStack Query v5 (클라이언트 사이드 폴링)
- 차트: Recharts v3
- 폼: react-hook-form + zod (Phase 7에서 도입 완료)
- `tsc --noEmit`: PASS
- `npm run lint`: PASS (0 errors, 0 warnings)
- `next build`: PASS
- Playwright: 미설치 (msw는 devDep으로 설치되었으나 browser mode 미사용)
- `frontend/app/dashboard/page.tsx:44`: `ChartContainer empty={true}` placeholder
- `frontend/app/runs/[runId]/page.tsx`: 카드 나열 구조 (탭 없음)

## Non-Goals

- 새로운 백엔드 API 엔드포인트 추가
- WebSocket/SSE 실시간 스트리밍 도입
- 전체 E2E 테스트 커버리지 (smoke test 3개로 제한)
- 대시보드 레이아웃 전면 재설계
- `/runs` 목록 페이지 변경
- 전략/패턴 페이지 추가 개선
- 반응형 레이아웃 전면 재검증

## Hard Decisions

### D-1. Playwright `page.route()` 기반 API mock을 사용한다

- ~~MSW browser mode~~ → Playwright 네이티브 `page.route()` interception으로 변경.
- 변경 사유: MSW Service Worker의 `worker.start()`가 비동기라 초기 fetch를 놓칠 수 있음 (race condition). Playwright `page.route()`는 페이지 로드 전에 등록되므로 race-free.
- Playwright 실행 시 `next build` 결과를 `next start`로 띄우고, `page.route()`로 API 요청을 가로챈다.
- MSW는 devDependency로 유지 (향후 unit/integration test에서 Node adapter 활용 가능).
- 실 백엔드 없이 CI/로컬에서 모두 재현 가능.

### D-2. Dashboard equity chart는 기존 폴링 구조를 그대로 사용한다

- 새로운 API 엔드포인트를 추가하지 않는다.
- **Go/No-Go Gate 결과: Go** — `getDashboardPositions()` 응답에서 equity 파생 가능.
- 파생 공식: `totalValue = Number(cash) + Σ(Number(quantity) × Number(average_cost) + Number(unrealized_pnl ?? 0))`
- `useDashboardPolling` 훅에서 polling 응답마다 portfolio value를 계산하여 시계열 누적 (최대 300포인트, 5초 throttle).
- 한계: 페이지 새로고침 시 누적 데이터 초기화 (서버 측 시계열 API가 추가되면 교체 가능).
- 실시간 스트리밍(WebSocket/SSE)은 범위 밖이다.
- 데이터가 없는 경우(백엔드 미연결, 포지션 없음) graceful empty 상태를 유지한다.

### D-3. `/runs/[runId]` 탭 레이아웃은 기존 컴포넌트를 재조합한다

- 현재 카드 나열 구조에 이미 존재하는 차트/테이블 컴포넌트를 탭으로 재조합한다.
- 컴포넌트 내부 로직은 변경하지 않는다.
- Base UI의 `Tabs` 프리미티브 또는 shadcn/ui 래퍼를 사용한다.

## Product Requirements

### PR-7.5-1. Playwright e2e 하네스 구축

- `frontend/e2e/` 디렉토리에 Playwright 테스트를 작성한다.
- `frontend/playwright.config.ts`를 생성하여 `next start` 기반 로컬 서버를 타겟으로 구성한다.
- Playwright `page.route()` 기반 API mock 핸들러(`frontend/e2e/mocks/handlers.ts`)를 작성하여 다음 엔드포인트를 mock한다:
  - `GET /api/v1/dashboard/status`
  - `GET /api/v1/dashboard/positions`
  - `GET /api/v1/dashboard/events`
  - `GET /api/v1/backtests/:runId` (상세)
- `package.json`에 `test:e2e` 스크립트를 추가한다.
- Smoke test 3개를 작성한다:
  1. 홈 페이지(`/`) 로드 및 대시보드 링크 존재 확인
  2. 대시보드(`/dashboard`) 로드 및 MetricCard 렌더링 확인
  3. 백테스트 상세(`/runs/[runId]`) 로드 및 상세 컨테이너 렌더링 확인
- 참고: `/runs` 목록 페이지는 서버 API가 아닌 `runsStore`(localStorage)에서 run id를 읽어 개별 fetch하는 구조이므로, smoke test 대상을 `/runs/[runId]` 상세 페이지로 변경한다. 테스트 시 `runsStore` localStorage seed를 주입하거나 deterministic route를 사용한다.
- `npm run test:e2e`로 3개 smoke test가 모두 통과해야 한다.

### PR-7.5-2. Dashboard Portfolio Equity Chart

- `frontend/app/dashboard/page.tsx`의 equity chart placeholder를 실제 차트로 교체한다.
- 차트는 기존 polling 데이터(`getDashboardStatus` 또는 `getDashboardPositions` 응답)에서 equity 값을 파생하여 Recharts로 렌더링한다.
- **Go/No-Go Gate**: Step B1에서 API 응답에 equity 파생 가능한 필드가 확인되지 않으면 B2/B3를 보류하고, 해당 항목만 Phase 8로 이동한다. 현재 `DashboardStatus`/`PositionsResponse` 타입에는 `totalValue`/`equity` 시계열 필드가 없으므로, 클라이언트 누적 방식의 신뢰성을 평가한 뒤 go/no-go를 결정한다.
- 데이터가 없는 경우 현재와 같이 `ChartContainer empty` 상태를 표시한다.
- 차트 컴포넌트는 `components/dashboard/EquityChart.tsx`로 분리한다.

### PR-7.5-3. `/runs/[runId]` 탭 기반 레이아웃

- 현재 카드 나열 구조를 다음 4개 탭으로 재조합한다:
  - **Summary** 탭: RunSummaryGrid (항상 렌더) + StatTile 그리드 (analytics 있을 때만, 없으면 안내 메시지)
  - **Charts** 탭: EquityCurveChart + DrawdownChart (result 기반, 항상 렌더) + TradeScatterChart (analytics 있을 때만, 없으면 안내 메시지)
  - **Trades** 탭: TradesTable (analytics 있을 때만, 없으면 안내 메시지) + FillsTable (result 기반, 항상 렌더)
  - **Signals** 탭: SignalsTable (항상 렌더)
- 탭 컴포넌트는 기존 `frontend/components/ui/tabs.tsx`(Base UI 래퍼, `Tabs`/`TabsList`/`TabsTrigger`/`TabsContent` export 확인됨)를 재사용한다.
- 기존 컴포넌트(`EquityCurveChart`, `DrawdownChart`, `TradeScatterChart`, `SignalsTable`, `FillsTable`, `TradesTable`)의 내부 로직은 변경하지 않는다.
- `run.result`가 없는 경우(미완료 실행): `RunDetailTabs`가 `null`을 반환한다.
- analytics unavailable 처리 원칙: 탭 자체를 비활성화하지 않는다. 각 탭 내에서 analytics-의존 컴포넌트만 조건부 렌더링하고, result 기반 컴포넌트는 항상 표시한다.

## Scope By Epic

### Epic A. Playwright e2e 하네스

목표: CI/로컬에서 백엔드 없이 재현 가능한 e2e smoke test 환경을 구성한다.

포함:
- Playwright 설치 및 `playwright.config.ts` 설정
- Playwright `page.route()` 기반 API mock 핸들러 (MSW browser mode 대신 채택 — race-free)
- Smoke test 3개 작성 및 통과
- `package.json`에 `test:e2e` 스크립트 추가

제외:
- 전체 E2E 테스트 커버리지
- CI/CD 파이프라인 연동
- MSW browser mode / Service Worker 등록 (race condition 문제로 미채택)

### Epic B. Dashboard Equity Chart

목표: 대시보드 portfolio 영역의 placeholder를 실제 차트로 교체한다.

포함:
- polling 응답에서 equity 시계열 파생 로직
- `EquityChart` 컴포넌트 신규 구현
- `dashboard/page.tsx` 교체

제외:
- 새로운 백엔드 API 추가
- WebSocket/SSE 기반 실시간 스트리밍
- 대시보드 전체 레이아웃 변경

### Epic C. Runs 상세 탭 레이아웃

목표: `/runs/[runId]` 페이지를 PRD 명세의 탭 기반 구조로 전환한다.

포함:
- 기존 `components/ui/tabs.tsx` 재사용 (Base UI 래퍼 확인됨)
- `RunDetailTabs` 컴포넌트 구현
- 기존 컴포넌트 탭에 재조합
- analytics unavailable 상태 처리 (empty state)

제외:
- 차트/테이블 컴포넌트 내부 로직 변경
- 새로운 API 연동
- Tabs 프리미티브 신규 작성 (이미 존재)

## Impacted Files

### 신규 생성
- `frontend/playwright.config.ts`
- `frontend/e2e/smoke.spec.ts`
- `frontend/e2e/mocks/handlers.ts`
- `frontend/e2e/mocks/setup.ts` (mock setup re-export)
- `frontend/components/dashboard/EquityChart.tsx`
- `frontend/components/runs/RunDetailTabs.tsx`

### 수정 대상
- `frontend/package.json` — `test:e2e` 스크립트, Playwright 의존성 추가
- `frontend/app/dashboard/page.tsx` — placeholder 교체
- `frontend/app/runs/[runId]/page.tsx` — 카드 → 탭 레이아웃 전환
- `frontend/components/ui/tabs.tsx` — 이미 존재 확인됨, 재사용 (인터페이스 적합성만 확인)

### 문서
- `prd/phase_7_5_task.md` (실행 추적)

## Delivery Slices

### Slice A. Playwright e2e 하네스
- 의존성 설치, config 설정, `page.route()` mock 핸들러, smoke test 3개 작성

### Slice B. Dashboard Equity Chart
- polling 데이터에서 equity 파생, EquityChart 컴포넌트, placeholder 교체

### Slice C. Runs 상세 탭 레이아웃
- Tabs 래퍼 확인/추가, RunDetailTabs 구현, page.tsx 전환

### Slice D. 최종 검증
- `tsc --noEmit`, `lint`, `next build`, `test:e2e` 전체 통과 확인

## Success Metrics

- `npm run test:e2e`로 smoke test 3개 이상 통과
- `frontend/app/dashboard/page.tsx`에 더 이상 `empty={true}` placeholder가 없음 (데이터 없는 경우 제외)
- `frontend/app/runs/[runId]/page.tsx`가 탭 기반 레이아웃으로 동작
- `tsc --noEmit` PASS
- `npm run lint` PASS (0 errors, 0 warnings)
- `next build` PASS

## Risks and Follow-up

- ~~MSW Service Worker 모드 race condition~~ → Playwright `page.route()` 채택으로 리스크 해소. MSW는 devDependency로 유지하되 browser mode는 사용하지 않는다.
- Dashboard equity chart용 시계열 데이터가 기존 polling 응답에 없을 수 있다. 현재 `DashboardStatus`/`PositionsResponse`에는 equity 시계열 필드가 없으므로, **Step B1을 go/no-go gate로 운영**하여 신뢰 가능한 파생 공식이 확인되지 않으면 B2/B3를 보류하고 Phase 8로 이동한다.
- ~~Base UI Tabs 컴포넌트가 `frontend/components/ui/`에 없으면 신규 래퍼 추가 필요.~~ → `tabs.tsx`는 이미 존재 확인됨 (Base UI 래퍼, `Tabs`/`TabsList`/`TabsTrigger`/`TabsContent` export). 리스크 해소.
- Playwright는 Chromium 바이너리 다운로드를 포함하므로 초기 설치 시간이 길다. CI 환경에서는 Docker 이미지 또는 캐시 전략이 필요하다.
- `/runs` 목록 페이지는 서버 API 목록 엔드포인트가 아닌 `runsStore`(localStorage) 기반이므로, smoke test 시 localStorage seed 주입 또는 deterministic route(`/runs/[runId]`)를 사용해야 한다.
