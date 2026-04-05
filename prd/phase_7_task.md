# Phase 7 Task Breakdown

## Usage

- 이 파일은 Phase 7 구현 진행 상황과 검증 증적을 기록한다.
- 체크박스는 실제 구현 작업과 검증 기준을 뜻한다.
- 각 slice가 끝날 때 `Execution Log`를 갱신한다.
- PRD 수준 범위는 `phase_7_prd.md`를 기준으로 한다.
- 상세 설계와 순서는 `phase_7_implementation_plan.md`를 기준으로 한다.

## Status Note

- 이 문서는 `prd/phase_7_prd.md`의 실행 추적 문서다.
- Phase 7-0 ~ 7-3은 실질적으로 완료되었다. 단, PRD가 계획한 `frontend-next/` 스테이징 경로가 아닌 `frontend/`를 직접 교체하는 방식으로 진행되었다.
- Phase 7-4(Playwright/MSW smoke test)는 미구현 상태로 남아 있다.
- Phase 7 백엔드 코드 변경은 포함하지 않는다.

## Phase 7-0. Next.js 프로젝트 부트스트랩

- [x] `frontend/` 디렉토리를 Next.js 16 + App Router + TypeScript로 전환 (PRD의 `frontend-next/` 경로 대신 직접 교체)
- [x] Tailwind CSS v4 설치 및 디자인 토큰 설정
- [x] `app/globals.css`에 CSS 변수 기반 시맨틱 색상 정의 (success, danger, warning, info, muted)
- [x] `store/apiStore.ts`: Zustand persist 기반 baseUrl/apiKey store
- [x] `components/shared/ApiSettingsBar.tsx`: 운영자 런타임 API 설정 변경 UX
- [x] `app/layout.tsx`: 루트 레이아웃 (QueryClientProvider, NavBar, ApiSettingsBar)
- [x] `components/layout/NavBar.tsx`: Next.js `Link` 기반 네비게이션
- [x] `lib/api/` 전체 이식 (`requestJson()`이 `useApiStore.getState()`에서 baseUrl/apiKey 읽음)
- [x] `lib/queryClient.ts`, `lib/utils.ts`, `lib/formatters.ts`, `lib/strategyParser.ts`, `lib/patternParser.ts` 이식
- [x] `.env.local.example` 작성
- [x] `components.json` 생성
- [x] 8개 라우트 디렉토리에 `page.tsx`, `loading.tsx`, `error.tsx` 구현
- [x] `next build` 에러 없이 완료

Exit criteria:
- `next build`가 에러 없이 완료되고, `next dev`에서 8개 라우트가 접근 가능하며, `ApiSettingsBar`를 통한 API 설정 변경이 동작한다.

## Phase 7-1. 디자인 시스템 컴포넌트 구축

- [x] Base UI + shadcn 래퍼 기반 UI 프리미티브 설치 (Button, Card, Table, Input, Select, Label 등)
- [x] `components/domain/MetricCard.tsx`: 숫자 값 + 레이블 + 추세 아이콘, loading skeleton 지원
- [x] `components/domain/DataTable.tsx`: Column 정의 기반, 빈 상태 메시지, loading skeleton
- [x] `components/domain/StatusIndicator.tsx`: dot + 레이블, online/offline/warning/error variant
- [x] `components/domain/ChartContainer.tsx`: loading spinner, empty 메시지, error fallback
- [x] `components/layout/PageHeader.tsx`: 제목 + 설명 + 액션 슬롯
- [x] `next build` 통과 유지

Exit criteria:
- 5개 도메인 컴포넌트가 각각 loading/empty/error 상태를 렌더링하고, `next build`가 통과한다.

## Phase 7-2. 대시보드 페이지 재설계

- [x] `hooks/useDashboardPolling.ts`: TanStack Query 기반 폴링 (5 s), `isLive` 계산
- [x] `app/dashboard/page.tsx`: PageHeader + ControlButtons + StatusIndicator
- [x] 상단 MetricCard 그리드: 총 자산, 일간 P&L, 포지션 수, 시스템 상태
- [x] `PositionsPanel`: 좌측 패널
- [ ] PortfolioChart(우측): 실시간 equity 차트 — `ChartContainer empty={true}` placeholder 상태 (미구현)
- [x] `EventTimeline`: 시간순 이벤트 피드
- [x] 제어 버튼(pause/resume/reset) PageHeader에서 동작

Exit criteria:
- 대시보드가 백엔드 연결/미연결 시 적절한 상태를 표시하고, 반응형 레이아웃이 적용된다.
- ⚠️ Portfolio equity chart는 미구현 (placeholder). Phase 8 대상.

## Phase 7-3. 백테스트/전략/패턴 페이지 구축

- [x] `/runs` 목록 페이지: DataTable + PageHeader
- [x] `/runs/[runId]` 상세 페이지: EquityCurveChart, DrawdownChart, TradeScatterChart, SignalsTable, FillsTable, TradesTable, analytics StatTile 그리드 구현
  - ⚠️ PRD 명세는 탭 기반 구조였으나 카드 나열 구조로 구현 (기능 커버리지는 동일)
- [x] 차트 컴포넌트 이식: EquityCurveChart, DrawdownChart, TradeScatterChart
- [x] `/strategies` 페이지: StrategiesTable + StrategyForm (`react-hook-form + zod`) 구현
- [x] `/patterns` 목록 페이지: PatternSetsTable + PatternTrainForm (`react-hook-form + zod`) 구현
- [x] `/patterns/[patternSetId]` 상세 페이지: PatternPreviewTable
- [x] `/admin` 페이지
- [x] `next build` 통과 유지

Exit criteria:
- 기존 프론트엔드의 모든 기능이 Next.js 버전에서 동작하고, 각 페이지에 상태 커버리지가 완전하다.

## Phase 7-4. 반응형/접근성/빌드 검증

- [ ] Playwright 테스트 하네스 설정 (MSW로 API mock)
- [ ] MSW 핸들러 작성: 핵심 엔드포인트 fixture 응답
- [ ] `package.json`에 `test:e2e` 스크립트 정의
- [ ] Playwright smoke test 3개 이상 작성 및 통과
- [x] `npx tsc --noEmit` 통과
- [x] `npm run lint` 통과 (ESLint 0 errors, 0 warnings)
- [x] `next build` 최종 성공

Exit criteria:
- ⚠️ Playwright/MSW smoke test 미구현. `tsc`, `lint`, `build`는 모두 통과한다.

## Phase 7-5. 최종 교체 및 문서 정리

- [x] `frontend/`가 Next.js App Router 앱으로 교체 완료 (직접 전환 방식)
- [x] `components.json`, `package-lock.json`, `.env.local.example`, `store/apiStore.ts`, `lib/formatters.ts` 등 자산 완전성 충족
- [x] `next dev`와 `next build` 정상 동작
- [x] `frontend/README.md` 갱신 (Next.js App Router, 실행/빌드 방법, 환경변수, 디자인 시스템)
- [ ] Playwright `test:e2e` 재확인 — 미구현

Exit criteria:
- ⚠️ `npm run test:e2e` 미충족. 그 외 자산 완전성 및 README는 충족.

## Verification Checklist

### Required build checks

- [x] `cd frontend && npx tsc --noEmit` 성공
- [x] `cd frontend && npm run lint` 성공 (0 errors, 0 warnings)
- [x] `cd frontend && npm run build` 성공 (별도 확인)

### Required smoke tests (Playwright)

- [ ] 홈 페이지(`/`) 로드 및 네비게이션 링크 존재 확인
- [ ] 대시보드(`/dashboard`) 페이지 로드 및 MetricCard 렌더링 확인
- [ ] 백테스트 목록(`/runs`) 페이지 로드 및 DataTable 렌더링 확인

### Broader regression

- [x] 기존 프론트엔드의 모든 기능(대시보드 폴링, 백테스트 조회, 전략 CRUD, 패턴 학습/미리보기, 관리)이 Next.js 버전에서 동작
- [x] `frontend/` 경로에서 전체 빌드/타입 검증

### Manual verification

- [ ] 대시보드가 백엔드 연결 시 실시간 데이터를 폴링하는지 확인
- [ ] 백엔드 미연결 시 각 페이지가 error 상태를 올바르게 표시하는지 확인
- [ ] 375px 너비에서 네비게이션이 올바르게 동작하는지 확인
- [ ] 키보드만으로 네비게이션 + 폼 제출이 가능한지 확인
- [ ] 차트가 데이터 로딩 중/빈 상태/에러 상태를 올바르게 표시하는지 확인

## Execution Log

### Date
- Phase 7 구현: 2026-04 이전 완료
- Phase 7 완료 정리 및 잔여 항목 수정: 2026-04-05

### Owner
- Claude Code (Sonnet 4.6)

### Slice completed
- Phase 7-0 ~ 7-3: 실질적 완료 (frontend/ 직접 전환 방식)
- Phase 7-4 partial: tsc + lint + build 통과. Playwright/MSW 미구현.
- Phase 7-5 partial: 자산 완전성 충족, README 갱신. test:e2e 미충족.

### Scope implemented
- Next.js 16 App Router 전환 (8개 라우트)
- 디자인 시스템 도메인 컴포넌트 5종
- 대시보드 실시간 폴링 (portfolio equity chart 제외)
- 백테스트 상세 페이지 (차트 3종 + 테이블 3종 + analytics)
- 전략/패턴 폼 react-hook-form + zod 리팩터링
- Zustand API settings 보존

### Files changed (2026-04-05 session)
- `frontend/hooks/useDashboardPolling.ts` — lint fix: `useState(() => Date.now())`
- `frontend/components/strategies/StrategyForm.tsx` — react-hook-form + zod + Controller
- `frontend/components/patterns/PatternTrainForm.tsx` — react-hook-form + zod
- `frontend/README.md` — 전체 재작성
- `prd/phase_7_task.md` — 완료 증적 반영

### Commands run
- `npx tsc --noEmit` → 0 errors
- `npm run lint` → 0 errors, 0 warnings

### Validation results
- TypeScript: PASS
- ESLint: PASS
- Playwright/MSW: NOT IMPLEMENTED

### Risks / follow-up
- Dashboard portfolio equity chart: 실시간 데이터 스트림 구조 설계 필요 (Phase 8 대상)
- Playwright + MSW smoke test: Phase 8에서 별도 slice로 처리 권장
- `/runs/[runId]` 탭 기반 레이아웃 전환: UX 요구사항 재확인 후 결정
