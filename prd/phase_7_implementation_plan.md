# Phase 7 Implementation Plan

## Goal

Phase 7은 현재 Vite SPA 프론트엔드를 Next.js App Router 기반으로 재구축하고, B2B SaaS 수준의 디자인 시스템을 적용하여 운영자 친화적 프론트엔드를 완성하는 단계다.

가장 중요한 구현 원칙은 다음 다섯 가지다.

1. 백엔드 API(`/api/v1/*`)는 변경하지 않는다. 프론트엔드만 교체한다.
2. 서버 컴포넌트는 레이아웃, 정적 페이지 쉘, 비인터랙티브 래퍼에 사용한다. 데이터 기반 화면은 `use client` 경계 안에서 TanStack Query로 처리한다.
3. 데이터 페칭은 기존 TanStack Query 클라이언트 패턴을 유지한다(SSR 데이터 페칭 도입 안 함). `requestJson()`은 `useApiStore`에서 baseUrl/apiKey를 읽는 구조를 보존한다.
4. 디자인은 `frontend-product-designer` 스킬의 원칙(정보 계층 → 컴포넌트 → 구현 → 검증)을 따른다.
5. 기존 API 클라이언트, 타입 정의, Recharts 차트 로직은 최대한 재활용한다.

## Preconditions

구현을 시작하기 전에 다음 범위를 고정한다.

- Phase 7 구현 범위는 프론트엔드 전환과 디자인 고도화에 한정한다. 백엔드 변경은 없다.
- `frontend-next/` 디렉토리에 독립적으로 구축하고, 완성 후 `frontend/`를 교체한다.
- Next.js 15 + App Router + TypeScript + Tailwind CSS v4 + shadcn/ui를 사용한다.
- TanStack Router는 제거하고 Next.js 파일 기반 라우팅으로 전환한다.
- TanStack Query는 유지한다(클라이언트 사이드 데이터 페칭).
- Zustand는 유지한다. 특히 `apiStore`는 API 클라이언트의 핵심 의존성이므로 반드시 이식한다.
- Recharts v2는 유지한다(`use client` 경계 내에서 사용).
- WebSocket/SSE, 인증, i18n은 범위 밖이다.

## Locked Design Decisions

### 1. Next.js App Router 디렉토리 구조는 기존 라우트를 1:1 매핑한다

```
app/
├── layout.tsx              ← 글로벌 레이아웃 + 프로바이더
├── page.tsx                ← / (홈)
├── dashboard/
│   ├── page.tsx            ← /dashboard
│   ├── loading.tsx
│   └── error.tsx
├── runs/
│   ├── page.tsx            ← /runs
│   ├── [runId]/
│   │   ├── page.tsx        ← /runs/[runId]
│   │   ├── loading.tsx
│   │   └── error.tsx
│   ├── loading.tsx
│   └── error.tsx
├── strategies/
│   ├── page.tsx            ← /strategies
│   ├── loading.tsx
│   └── error.tsx
├── patterns/
│   ├── page.tsx            ← /patterns
│   ├── [patternSetId]/
│   │   ├── page.tsx        ← /patterns/[patternSetId]
│   │   ├── loading.tsx
│   │   └── error.tsx
│   ├── loading.tsx
│   └── error.tsx
└── admin/
    ├── page.tsx            ← /admin
    ├── loading.tsx
    └── error.tsx
```

### 2. 컴포넌트 디렉토리 구조는 계층별로 분리한다

```
components/
├── ui/                     ← shadcn/ui 기본 프리미티브 (Button, Input, Card 등)
├── domain/                 ← 트레이딩 도메인 복합 컴포넌트 (MetricCard, DataTable 등)
├── charts/                 ← Recharts 기반 차트 (use client)
├── dashboard/              ← 대시보드 전용 컴포넌트
├── runs/                   ← 백테스트 결과 전용 컴포넌트
├── strategies/             ← 전략 관리 전용 컴포넌트
├── patterns/               ← 패턴 관리 전용 컴포넌트
└── layout/                 ← 네비게이션, 사이드바, 페이지 헤더
```

### 3. 디자인 토큰은 Tailwind CSS 설정에 중앙화한다

- 시맨틱 색상: `--color-success`, `--color-danger`, `--color-warning`, `--color-info`, `--color-muted`
- 숫자 전용 폰트: `font-mono`(tabular-nums)로 가격/수량/비율 표시
- 간격: 4px 기반 시스템, compact(2)/default(4)/relaxed(6) density variant
- 다크 테마 기본, zinc 기반 그레이스케일 유지

### 4. API 클라이언트는 기존 코드를 이식하되 경로를 정리한다

- `frontend/src/api/` 코드를 `frontend-next/lib/api/`로 이식한다.
- `client.ts`의 base URL은 환경변수(`NEXT_PUBLIC_API_BASE_URL`)로 설정한다.
- 타입 정의(`types.ts`)는 그대로 유지한다.

### 5. 폼은 react-hook-form + zod 패턴을 유지하되 신규 의존성으로 추가한다

- 기존 프론트엔드에 react-hook-form/zod가 package.json에 없으므로 신규 추가한다.
- 전략 생성/편집, 패턴 학습 폼에 적용한다.

## Contract Deltas

## A. 프로젝트 구조 전환

대상:
- `frontend-next/package.json`
- `frontend-next/next.config.ts`
- `frontend-next/tsconfig.json`
- `frontend-next/tailwind.config.ts`
- `frontend-next/app/layout.tsx`

필수 변화:
- Vite + TanStack Router → Next.js App Router 전환
- 빌드 스크립트: `next dev`, `next build`, `next start`
- 경로 별칭: `@/` → `frontend-next/` root

비고:
- `next.config.ts`에서 API rewrites 또는 CORS proxy 설정이 필요할 수 있다.

## B. 디자인 시스템 계약

대상:
- `frontend-next/tailwind.config.ts`
- `frontend-next/app/globals.css`
- `frontend-next/components/ui/` (shadcn/ui)
- `frontend-next/components/domain/` (복합 컴포넌트)

필수 변화:
- 디자인 토큰(색상, 타이포그래피, 간격)을 Tailwind 설정에 정의
- shadcn/ui 컴포넌트 테마를 토큰에 맞게 커스터마이즈
- 도메인 복합 컴포넌트(MetricCard, DataTable, StatusIndicator, ChartContainer, PageHeader) 구현

비고:
- 모든 도메인 컴포넌트는 loading/empty/error props를 지원해야 한다.

## C. 페이지별 UI 계약

대상:
- `frontend-next/app/dashboard/page.tsx`
- `frontend-next/app/runs/page.tsx`
- `frontend-next/app/runs/[runId]/page.tsx`
- `frontend-next/app/strategies/page.tsx`
- `frontend-next/app/patterns/page.tsx`
- `frontend-next/app/admin/page.tsx`

필수 변화:
- 각 페이지가 PageHeader + 콘텐츠 영역 구조를 따른다
- 데이터 기반 화면은 loading/empty/error 상태를 모두 포함한다
- 대시보드는 MetricCard 그리드 + 2컬럼 + 타임라인 구조
- 백테스트 상세는 탭 기반 구조

비고:
- 기존 백엔드 API 응답 shape는 변경하지 않는다.

## D. 빌드/검증 계약

대상:
- `frontend-next/package.json`
- `frontend-next/playwright.config.ts` (또는 유사)
- `frontend-next/.eslintrc.*`

필수 변화:
- `next build` 에러 없음
- `tsc --noEmit` 통과
- ESLint 통과
- Playwright smoke test (최소 3 페이지)

## Sequenced Implementation

### Step 0. Next.js 프로젝트 부트스트랩

목적:
- `frontend-next/` 디렉토리에 빌드 가능한 Next.js 프로젝트를 생성한다.

파일:
- `frontend-next/package.json`
- `frontend-next/next.config.ts`
- `frontend-next/tsconfig.json`
- `frontend-next/tailwind.config.ts`
- `frontend-next/components.json` (shadcn/ui 설정)
- `frontend-next/.env.local.example`
- `frontend-next/app/globals.css`
- `frontend-next/app/layout.tsx`
- `frontend-next/app/page.tsx`
- `frontend-next/lib/api/client.ts`
- `frontend-next/lib/api/types.ts`
- `frontend-next/lib/queryClient.ts`
- `frontend-next/lib/utils.ts`
- `frontend-next/lib/formatters.ts`
- `frontend-next/lib/strategyParser.ts`
- `frontend-next/lib/patternParser.ts`
- `frontend-next/store/apiStore.ts`
- `frontend-next/components/shared/ApiSettingsBar.tsx`
- `frontend-next/components/layout/NavBar.tsx`

구체 작업:
- `create-next-app` 또는 수동으로 Next.js 15 프로젝트 초기화
- Tailwind CSS v4, shadcn/ui 설치 및 설정
- 디자인 토큰을 `tailwind.config.ts`와 `globals.css`에 정의
- `store/apiStore.ts` 이식: Zustand persist 기반 baseUrl/apiKey store, `NEXT_PUBLIC_API_BASE_URL`을 초기 기본값으로 사용
- `components/shared/ApiSettingsBar.tsx` 이식: 운영자 런타임 API 설정 변경 UX 보존
- 루트 레이아웃(`app/layout.tsx`)에 글로벌 프로바이더(QueryClientProvider), 네비게이션, 다크 테마, `ApiSettingsBar` 적용
- 기존 API 클라이언트/타입 코드를 `lib/api/`로 이식 (`requestJson()`이 `useApiStore.getState()`에서 baseUrl/apiKey를 읽는 구조 유지)
- 기존 파서/포매터 유틸(`formatters.ts`, `strategyParser.ts`, `patternParser.ts`)을 `lib/`로 이식
- `.env.local.example`에 `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1` 예시 포함
- 모든 라우트 디렉토리에 빈 `page.tsx`, `loading.tsx`, `error.tsx` 스캐폴드 생성
- `loading.tsx`는 route-level fallback(페이지 초기 로드/번들 로딩)으로 사용, query-level 상태는 각 클라이언트 컴포넌트 내부에서 처리
- `next dev` 실행 확인, `next build` 성공 확인

종료 조건:
- `next build`가 에러 없이 완료된다.
- `next dev`에서 8개 라우트가 모두 접근 가능하다.
- 루트 레이아웃에 `ApiSettingsBar`가 표시되고, base URL 변경이 API 호출에 반영된다.
- API 클라이언트가 기존 백엔드로 요청을 보낼 수 있다.

### Step 1. 디자인 시스템 컴포넌트 구축

목적:
- shadcn/ui 프리미티브 위에 트레이딩 도메인 전용 복합 컴포넌트를 구축한다.

파일:
- `frontend-next/components/ui/` (shadcn/ui 컴포넌트)
- `frontend-next/components/domain/MetricCard.tsx`
- `frontend-next/components/domain/DataTable.tsx`
- `frontend-next/components/domain/StatusIndicator.tsx`
- `frontend-next/components/domain/ChartContainer.tsx`
- `frontend-next/components/layout/PageHeader.tsx`

구체 작업:
- shadcn/ui CLI로 필요한 기본 컴포넌트 설치 (Button, Card, Table, Tabs, Badge, Input, Select, Dialog, Label, Tooltip)
- shadcn/ui 테마를 디자인 토큰에 맞게 커스터마이즈
- `MetricCard`: 숫자 값 + 레이블 + 추세 아이콘 + 비교값, loading skeleton 지원
- `DataTable`: Column 정의 기반, 정렬/필터/페이지네이션, 빈 상태 메시지, loading skeleton
- `StatusIndicator`: dot + 레이블, online/offline/warning/error variant
- `ChartContainer`: 제목 + 차트 영역, loading spinner, empty 메시지, error fallback
- `PageHeader`: 제목 + 설명 + 액션 슬롯

종료 조건:
- 각 도메인 컴포넌트가 loading, empty, error 상태를 모두 렌더링한다.
- `next build` 통과가 유지된다.

### Step 2. 대시보드 페이지 재설계

목적:
- 라이브 대시보드를 MetricCard 그리드 + 2컬럼 + 타임라인 구조로 재구축한다.

파일:
- `frontend-next/app/dashboard/page.tsx`
- `frontend-next/app/dashboard/loading.tsx`
- `frontend-next/app/dashboard/error.tsx`
- `frontend-next/components/dashboard/DashboardMetrics.tsx`
- `frontend-next/components/dashboard/PositionsPanel.tsx`
- `frontend-next/components/dashboard/PortfolioChart.tsx`
- `frontend-next/components/dashboard/EventTimeline.tsx`
- `frontend-next/components/dashboard/ControlButtons.tsx`
- `frontend-next/hooks/useDashboardPolling.ts`

구체 작업:
- 기존 `useDashboardPolling` 훅 이식 (TanStack Query 유지)
- 상단 MetricCard 그리드: 총 자산, 일간 P&L, 포지션 수, 시스템 상태(StatusIndicator)
- 중단 2컬럼: 좌측 포지션 DataTable, 우측 포트폴리오 구성 차트(ChartContainer + Recharts)
- 하단 EventTimeline: 시간순 이벤트 피드
- PageHeader에 ControlButtons(pause/resume/reset) + 연결 상태 StatusIndicator 통합
- 반응형: mobile에서 단일 컬럼, desktop에서 2컬럼

종료 조건:
- 대시보드가 백엔드 연결 시 실시간 데이터를 표시한다.
- 백엔드 미연결 시 error 상태를 표시한다.
- 375px, 1280px 너비에서 의도적 레이아웃이 적용된다.

### Step 3. 백테스트/전략/패턴 페이지 구축

목적:
- 분석 및 관리 페이지를 도메인 컴포넌트를 활용하여 재구축한다.

파일:
- `frontend-next/app/runs/page.tsx`
- `frontend-next/app/runs/[runId]/page.tsx`
- `frontend-next/app/strategies/page.tsx`
- `frontend-next/app/patterns/page.tsx`
- `frontend-next/app/patterns/[patternSetId]/page.tsx`
- `frontend-next/app/admin/page.tsx`
- `frontend-next/components/runs/` (RunSummaryGrid, FillsTable, SignalsTable, TradesTable)
- `frontend-next/components/charts/` (EquityCurveChart, DrawdownChart, TradeScatterChart)
- `frontend-next/components/strategies/` (StrategyForm, StrategiesTable)
- `frontend-next/components/patterns/` (PatternSetsTable, PatternTrainForm, PatternPreviewTable)

구체 작업:
- `/runs` 목록: DataTable + PageHeader, 실행 이력 표시
- `/runs/[runId]` 상세: Tabs 컴포넌트로 Summary/Equity/Trades/Signals 탭 구현
  - Summary: MetricCard 그리드 (return, max_drawdown, volatility, win_rate)
  - Equity: ChartContainer + EquityCurveChart + DrawdownChart 오버레이
  - Trades: DataTable (거래 내역) + TradeScatterChart
  - Signals: DataTable (시그널 이벤트)
- `/strategies`: StrategiesTable + StrategyForm(react-hook-form + zod)
- `/patterns`: PatternSetsTable + PatternTrainForm
- `/patterns/[patternSetId]`: PatternPreviewTable
- `/admin`: 기존 기능 이식
- 모든 차트 컴포넌트는 `use client` + ChartContainer로 래핑

종료 조건:
- 기존 프론트엔드의 모든 기능이 Next.js 버전에서 동작한다.
- 각 페이지에 loading/empty/error 상태가 포함된다.

### Step 4. 반응형/접근성/빌드 검증

목적:
- 전체 애플리케이션의 반응형 디자인, 접근성, 빌드를 검증한다.

파일:
- 모든 페이지 및 컴포넌트 (조정)
- `frontend-next/e2e/smoke.spec.ts` (Playwright)
- `frontend-next/.eslintrc.cjs` 또는 `eslint.config.mjs`

구체 작업:
- Playwright 테스트 하네스 결정: MSW(Mock Service Worker)로 API 응답을 mock하여 백엔드 의존 없이 실행
- `package.json`에 `test:e2e` 스크립트 정의 (`npx playwright test`)
- MSW 핸들러 작성: `/api/v1/dashboard/status`, `/api/v1/backtests` 등 핵심 엔드포인트의 fixture 응답
- 375px(mobile), 768px(tablet), 1280px(desktop)에서 각 페이지 레이아웃 검증 및 조정
- 키보드 네비게이션 검증: Tab 순서, Enter/Space 동작, 포커스 표시
- 시맨틱 HTML 검증: heading 계층, landmark 영역, form label
- `next build` 최종 성공 확인
- `tsc --noEmit` 통과 확인
- ESLint 설정 + 통과 확인
- Playwright smoke test 작성: 홈 페이지 로드, 대시보드 네비게이션, 백테스트 목록 로드
- react-hook-form + zod 의존성 추가 확인

종료 조건:
- `next build` 에러 없음
- `tsc --noEmit` 에러 없음
- ESLint 에러 없음
- `npm run test:e2e`로 Playwright smoke test 3개 이상 통과 (MSW mock 기반, 실 백엔드 불필요)
- 반응형 breakpoint별 의도적 레이아웃 확인

### Step 5. 최종 교체 및 문서 정리

목적:
- `frontend-next/`를 `frontend/`로 교체하고 문서를 정리한다.

파일:
- `frontend/` (기존 제거)
- `frontend-next/` → `frontend/` (이동)
- `README.md`
- `prd/phase_7_task.md`

구체 작업:
- 기존 `frontend/` 백업 또는 git history 보존 후 제거
- `frontend-next/` → `frontend/` 이동
- 교체 후 자산 완전성 체크리스트 확인:
  - `components.json` (shadcn/ui 설정) 존재
  - `package-lock.json` 존재 및 `npm ci` 성공
  - `.env.local.example` 존재
  - `store/apiStore.ts` 존재 및 `requestJson()`이 store를 정상 참조
  - `lib/formatters.ts`, `lib/strategyParser.ts`, `lib/patternParser.ts` 존재
  - `tsconfig.json`의 path alias(`@/`)가 새 디렉토리 구조에 맞게 설정
- `README.md` 프론트엔드 섹션 갱신 (Next.js App Router, 실행 방법, 빌드 방법, 환경변수 설명)
- task.md에 execution log 기록
- 최종 `next build` + `npm run test:e2e` 재확인

종료 조건:
- `frontend/`에서 `next dev`와 `next build`가 모두 동작한다.
- `npm run test:e2e`가 통과한다.
- 자산 완전성 체크리스트의 모든 항목이 확인된다.
- README가 새로운 프론트엔드 구조를 정확히 설명한다.

## Validation Matrix

### Required build checks

- `cd frontend-next && npm run build` (next build) 성공
- `cd frontend-next && npx tsc --noEmit` 성공
- `cd frontend-next && npm run lint` 성공

### Required smoke tests (Playwright)

- 홈 페이지(`/`) 로드 및 네비게이션 링크 존재 확인
- 대시보드(`/dashboard`) 페이지 로드 및 MetricCard 렌더링 확인
- 백테스트 목록(`/runs`) 페이지 로드 및 DataTable 렌더링 확인

### Manual verification

- 대시보드가 백엔드 연결 시 실시간 데이터를 폴링하는지 확인
- 백엔드 미연결 시 각 페이지가 error 상태를 올바르게 표시하는지 확인
- 375px 너비에서 네비게이션이 올바르게 동작하는지 확인
- 키보드만으로 네비게이션 + 폼 제출이 가능한지 확인
- 차트가 데이터 로딩 중/빈 상태/에러 상태를 올바르게 표시하는지 확인

## Recommended PR Slices

1. Next.js 부트스트랩 + 디자인 토큰 + 루트 레이아웃 + 라우트 스캐폴드
2. 디자인 시스템 복합 컴포넌트 (MetricCard, DataTable, StatusIndicator, ChartContainer, PageHeader)
3. 대시보드 재설계 + 폴링 훅 이식
4. 백테스트 목록/상세 + 차트 이식
5. 전략/패턴/관리 페이지 + 폼(react-hook-form + zod)
6. 반응형/접근성 조정 + Playwright smoke test + lint/type check
7. `frontend-next/` → `frontend/` 교체 + README 갱신

## Risks and Fallbacks

- Next.js 15와 React 19의 서버 컴포넌트에서 TanStack Query 사용 시 hydration 경고가 발생할 수 있다.

대응:
- Step 0에서 QueryClientProvider를 클라이언트 경계 컴포넌트(`Providers.tsx`)로 분리한다.

- Recharts가 서버 컴포넌트에서 import되면 빌드 에러가 발생한다.

대응:
- 모든 차트 컴포넌트에 `use client`를 명시하고, ChartContainer로 래핑하여 경계를 명확히 한다.

- 기존 API 클라이언트의 base URL 하드코딩이 Next.js 환경에서 문제를 일으킬 수 있다.

대응:
- Step 0에서 `NEXT_PUBLIC_API_BASE_URL` 환경변수 기반으로 이식한다.

- shadcn/ui CLI가 App Router 구조를 전제로 설치되므로, 컴포넌트 경로가 기존과 다를 수 있다.

대응:
- `components.json` 설정에서 경로를 명시적으로 지정한다.

- Playwright 테스트가 실행 중인 백엔드를 전제하면 CI에서 실패할 수 있다.

대응:
- Step 4에서 MSW(Mock Service Worker)로 API 응답을 mock한다. 실 백엔드 의존 없이 CI/로컬에서 `npm run test:e2e`로 재현 가능하도록 한다.
