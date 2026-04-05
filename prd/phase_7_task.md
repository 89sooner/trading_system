# Phase 7 Task Breakdown

## Usage

- 이 파일은 Phase 7 구현 진행 상황과 검증 증적을 기록한다.
- 체크박스는 실제 구현 작업과 검증 기준을 뜻한다.
- 각 slice가 끝날 때 `Execution Log`를 갱신한다.
- PRD 수준 범위는 `phase_7_prd.md`를 기준으로 한다.
- 상세 설계와 순서는 `phase_7_implementation_plan.md`를 기준으로 한다.

## Status Note

- 이 문서는 `prd/phase_7_prd.md`의 실행 추적 문서다.
- 현재 체크박스는 active backlog를 slice 단위로 분해한 것이며, 아직 구현 완료를 의미하지 않는다.
- Phase 7은 프론트엔드 전환 작업이므로 백엔드 코드 변경은 포함하지 않는다.

## Phase 7-0. Next.js 프로젝트 부트스트랩

- [ ] `frontend-next/` 디렉토리에 Next.js 15 + App Router + TypeScript 프로젝트 초기화
- [ ] Tailwind CSS v4 설치 및 `tailwind.config.ts`에 디자인 토큰(색상, 타이포그래피, 간격) 정의
- [ ] `app/globals.css`에 CSS 변수 기반 시맨틱 색상 정의 (success, danger, warning, info, muted)
- [ ] `store/apiStore.ts` 이식: Zustand persist 기반 baseUrl/apiKey store, `NEXT_PUBLIC_API_BASE_URL`을 초기 기본값으로 사용
- [ ] `components/shared/ApiSettingsBar.tsx` 이식: 운영자 런타임 API 설정 변경 UX 보존
- [ ] `app/layout.tsx`에 루트 레이아웃 구현 (다크 테마, QueryClientProvider, 글로벌 네비게이션, `ApiSettingsBar`)
- [ ] `components/layout/NavBar.tsx` 이식 및 Next.js `Link` 컴포넌트로 전환
- [ ] 기존 `frontend/src/api/` 코드를 `lib/api/`로 이식 (`requestJson()`이 `useApiStore.getState()`에서 baseUrl/apiKey를 읽는 구조 유지)
- [ ] `lib/queryClient.ts`, `lib/utils.ts`, `lib/formatters.ts`, `lib/strategyParser.ts`, `lib/patternParser.ts` 이식
- [ ] `.env.local.example`에 `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1` 예시 포함
- [ ] `components.json` (shadcn/ui 설정) 생성
- [ ] 8개 라우트 디렉토리에 빈 `page.tsx`, `loading.tsx`(route-level fallback), `error.tsx` 스캐폴드 생성
- [ ] `next dev` 실행 시 8개 라우트 모두 접근 가능 확인
- [ ] 루트 레이아웃에서 `ApiSettingsBar`가 표시되고 base URL 변경이 API 호출에 반영되는지 확인
- [ ] `next build` 에러 없이 완료 확인

Exit criteria:
- `next build`가 에러 없이 완료되고, `next dev`에서 8개 라우트가 접근 가능하며, `ApiSettingsBar`를 통한 API 설정 변경이 동작한다.

## Phase 7-1. 디자인 시스템 컴포넌트 구축

- [ ] shadcn/ui CLI로 기본 프리미티브 설치 (Button, Card, Table, Tabs, Badge, Input, Select, Dialog, Label, Tooltip)
- [ ] shadcn/ui 테마를 디자인 토큰(시맨틱 색상, 간격, 라운딩)에 맞게 커스터마이즈
- [ ] `components/domain/MetricCard.tsx` 구현: 숫자 값 + 레이블 + 추세 아이콘 + 비교값, loading skeleton 지원
- [ ] `components/domain/DataTable.tsx` 구현: Column 정의 기반, 정렬/필터/페이지네이션, 빈 상태 메시지, loading skeleton
- [ ] `components/domain/StatusIndicator.tsx` 구현: dot + 레이블, online/offline/warning/error variant
- [ ] `components/domain/ChartContainer.tsx` 구현: 제목 + 차트 영역, loading spinner, empty 메시지, error fallback
- [ ] `components/layout/PageHeader.tsx` 구현: 제목 + 설명 + 액션 슬롯
- [ ] 각 도메인 컴포넌트가 loading, empty, error props를 모두 처리하는지 확인
- [ ] `next build` 통과 유지 확인

Exit criteria:
- 5개 도메인 컴포넌트가 각각 loading/empty/error 상태를 렌더링하고, `next build`가 통과한다.

## Phase 7-2. 대시보드 페이지 재설계

- [ ] `hooks/useDashboardPolling.ts` 이식 (TanStack Query 기반 폴링 유지)
- [ ] `app/dashboard/page.tsx` 재구축: PageHeader + ControlButtons + StatusIndicator 통합
- [ ] 상단 MetricCard 그리드 구현: 총 자산, 일간 P&L, 포지션 수, 시스템 상태
- [ ] 중단 2컬럼 레이아웃: 좌측 PositionsPanel(DataTable), 우측 PortfolioChart(ChartContainer + Recharts)
- [ ] 하단 EventTimeline 구현: 시간순 이벤트 피드
- [ ] 대시보드 제어 버튼(pause/resume/reset)이 PageHeader 영역에서 동작 확인
- [ ] 연결 상태(live loop 활성 여부)가 StatusIndicator로 상시 표시 확인
- [ ] 백엔드 미연결 시 error 상태가 올바르게 표시되는지 확인
- [ ] 375px(mobile) 너비에서 단일 컬럼, 1280px(desktop)에서 2컬럼 레이아웃 확인

Exit criteria:
- 대시보드가 백엔드 연결/미연결 시 적절한 상태를 표시하고, 반응형 레이아웃이 적용된다.

## Phase 7-3. 백테스트/전략/패턴 페이지 구축

- [ ] `/runs` 목록 페이지: DataTable + PageHeader로 백테스트 실행 이력 표시
- [ ] `/runs/[runId]` 상세 페이지: Tabs 컴포넌트로 Summary/Equity/Trades/Signals 탭 구현
- [ ] Summary 탭: MetricCard 그리드 (return, max_drawdown, volatility, win_rate)
- [ ] Equity 탭: ChartContainer + EquityCurveChart + DrawdownChart
- [ ] Trades 탭: DataTable + TradeScatterChart
- [ ] Signals 탭: DataTable (시그널 이벤트)
- [ ] 차트 컴포넌트 이식: EquityCurveChart, DrawdownChart, TradeScatterChart (모두 `use client` + ChartContainer)
- [ ] `/strategies` 페이지: StrategiesTable + StrategyForm (react-hook-form + zod) 구현
- [ ] `/patterns` 목록 페이지: PatternSetsTable + PatternTrainForm 구현
- [ ] `/patterns/[patternSetId]` 상세 페이지: PatternPreviewTable 구현
- [ ] `/admin` 페이지: 기존 기능 이식
- [ ] 각 페이지에 loading/empty/error 상태가 포함되어 있는지 확인
- [ ] `next build` 통과 유지 확인

Exit criteria:
- 기존 프론트엔드의 모든 기능이 Next.js 버전에서 동작하고, 각 페이지에 상태 커버리지가 완전하다.

## Phase 7-4. 반응형/접근성/빌드 검증

- [ ] Playwright 테스트 하네스 결정: MSW(Mock Service Worker)로 API 응답을 mock하여 백엔드 의존 없이 실행
- [ ] MSW 핸들러 작성: `/api/v1/dashboard/status`, `/api/v1/backtests` 등 핵심 엔드포인트의 fixture 응답
- [ ] `package.json`에 `test:e2e` 스크립트 정의 (`npx playwright test`)
- [ ] 375px(mobile) 너비에서 모든 페이지 레이아웃 검증 및 조정
- [ ] 768px(tablet) 너비에서 모든 페이지 레이아웃 검증 및 조정
- [ ] 1280px(desktop) 너비에서 모든 페이지 레이아웃 검증 및 조정
- [ ] 키보드 네비게이션 검증: Tab 순서, Enter/Space 동작, 포커스 표시
- [ ] 시맨틱 HTML 검증: heading 계층(h1→h2→h3), landmark 영역, form label 연결
- [ ] `next build` 최종 성공 확인
- [ ] `npx tsc --noEmit` 통과 확인
- [ ] ESLint 설정 및 통과 확인
- [ ] Playwright smoke test 작성: 홈 페이지 로드 확인 (MSW mock 기반)
- [ ] Playwright smoke test 작성: 대시보드 네비게이션 및 MetricCard 렌더링 확인 (MSW mock 기반)
- [ ] Playwright smoke test 작성: 백테스트 목록 페이지 로드 및 DataTable 렌더링 확인 (MSW mock 기반)
- [ ] `npm run test:e2e`로 Playwright smoke test 3개 이상 통과 확인

Exit criteria:
- `next build`, `tsc --noEmit`, ESLint 모두 에러 없고, `npm run test:e2e`로 Playwright smoke test 3개 이상 통과한다 (MSW mock 기반, 실 백엔드 불필요).

## Phase 7-5. 최종 교체 및 문서 정리

- [ ] 기존 `frontend/` 디렉토리를 git history 보존 상태로 제거
- [ ] `frontend-next/` → `frontend/` 이동
- [ ] 교체 후 자산 완전성 체크리스트 확인:
  - [ ] `components.json` (shadcn/ui 설정) 존재
  - [ ] `package-lock.json` 존재 및 `npm ci` 성공
  - [ ] `.env.local.example` 존재
  - [ ] `store/apiStore.ts` 존재 및 `requestJson()`이 store를 정상 참조
  - [ ] `lib/formatters.ts`, `lib/strategyParser.ts`, `lib/patternParser.ts` 존재
  - [ ] `tsconfig.json`의 path alias(`@/`)가 새 디렉토리 구조에 맞게 설정
- [ ] 이동 후 `next dev`와 `next build` 재확인
- [ ] `npm run test:e2e` 재확인
- [ ] `README.md` 프론트엔드 섹션 갱신 (Next.js App Router, 실행/빌드 방법, 환경변수, 디자인 시스템 설명)
- [ ] Phase 7 종료 기준 충족 여부 최종 확인

Exit criteria:
- `frontend/`에서 `next dev`, `next build`, `npm run test:e2e`가 모두 동작하고, 자산 완전성 체크리스트가 충족되며, README가 새 구조를 정확히 설명한다.

## Verification Checklist

### Required build checks

- [ ] `cd frontend-next && npm run build` (next build) 성공
- [ ] `cd frontend-next && npx tsc --noEmit` 성공
- [ ] `cd frontend-next && npm run lint` 성공

### Required smoke tests (Playwright)

- [ ] 홈 페이지(`/`) 로드 및 네비게이션 링크 존재 확인
- [ ] 대시보드(`/dashboard`) 페이지 로드 및 MetricCard 렌더링 확인
- [ ] 백테스트 목록(`/runs`) 페이지 로드 및 DataTable 렌더링 확인

### Broader regression

- [ ] 기존 프론트엔드의 모든 기능(대시보드 폴링, 백테스트 조회, 전략 CRUD, 패턴 학습/미리보기, 관리)이 Next.js 버전에서 동작
- [ ] 최종 교체 후 `frontend/` 경로에서 전체 재검증

### Manual verification

- [ ] 대시보드가 백엔드 연결 시 실시간 데이터를 폴링하는지 확인
- [ ] 백엔드 미연결 시 각 페이지가 error 상태를 올바르게 표시하는지 확인
- [ ] 375px 너비에서 네비게이션이 올바르게 동작하는지 확인
- [ ] 키보드만으로 네비게이션 + 폼 제출이 가능한지 확인
- [ ] 차트가 데이터 로딩 중/빈 상태/에러 상태를 올바르게 표시하는지 확인

## Execution Log

### Date
- {구현 시작 시 날짜 기입}

### Owner
- {구현 주체}

### Slice completed
- {완료된 slice/step 기록}

### Scope implemented
- {구현된 범위 요약}

### Files changed
- {변경된 파일 목록}

### Commands run
- {실행한 검증 명령어와 결과}

### Validation results
- {검증 결과 요약}

### Risks / follow-up
- {잔여 리스크 및 후속 작업}
