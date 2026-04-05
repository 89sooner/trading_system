# Phase 7 PRD

관련 문서:
- 이전 phase 범위/결과: `prd/phase_6_prd.md`
- 상세 구현 계획: `prd/phase_7_implementation_plan.md`
- 실행 및 검증 기록: `prd/phase_6_task.md`
- 실행 추적: `prd/phase_7_task.md`
- 관련 히스토리: `prd/phase_4_task.md` (React 초기 도입)

## 문서 목적

이 문서는 현재 Vite SPA로 동작하는 프론트엔드를 Next.js App Router 기반 프로덕션 프론트엔드로 전환하고, B2B SaaS 수준의 디자인 시스템을 적용하여 운영 대시보드와 트레이딩 분석 UI를 고도화하는 `Phase 7` 범위를 정의한다.

Phase 7의 초점은 두 가지다.

1. **아키텍처 현대화**: Vite + TanStack Router SPA를 Next.js App Router로 전환하여 서버 컴포넌트, 레이아웃 중첩, 스트리밍 SSR, 코드 스플리팅 등 프로덕션 프론트엔드 기반을 확보한다.
2. **디자인 고도화**: `frontend-product-designer` 스킬의 UI 원칙과 B2B SaaS 디자인 패턴을 적용하여, 현재의 기능 중심 UI를 정보 계층이 명확하고 상태 커버리지가 완전한 운영자 친화적 인터페이스로 개선한다.

## Goal

Phase 7은 트레이딩 시스템 프론트엔드를 "기능이 동작하는 SPA"에서 "운영에 적합한 프로덕션 프론트엔드"로 전환하는 것을 목표로 한다.

구현은 반드시 다음 원칙을 지켜야 한다.

- 기존 백엔드 API(`/api/v1/*`)는 변경하지 않는다. 프론트엔드만 교체한다.
- Next.js App Router의 서버 컴포넌트를 기본으로 사용하고, 클라이언트 컴포넌트는 인터랙션이 필요한 경우에만 사용한다.
- `frontend-product-designer` 스킬의 디자인 원칙(정보 계층 우선, 실용적 B2B SaaS 스타일, 상태 커버리지, 접근성)을 따른다.
- 기존 shadcn/ui 컴포넌트를 재활용하되, 디자인 토큰과 레이아웃 시스템은 새로 정의한다.
- 기존 운영자 UX(`ApiSettingsBar` + `apiStore`를 통한 base URL/API key 런타임 변경)를 보존한다.
- 서버 컴포넌트는 레이아웃, 정적 페이지 쉘, 비인터랙티브 래퍼에 사용하고, 데이터 기반 화면은 대부분 클라이언트 컴포넌트 경계 안에서 TanStack Query로 처리한다.
- 모든 데이터 기반 화면에 이중 상태 커버리지를 적용한다: route-level fallback(`loading.tsx`/`error.tsx`)과 query-level fallback(TanStack Query의 isLoading/isError/isEmpty).
- 반응형 디자인을 의도적으로 설계한다(mobile-first → desktop).

## Current Baseline

- 프론트엔드는 `frontend/` 디렉토리에 Vite 6 + React 19 SPA로 구성되어 있다.
- 라우팅은 TanStack Router v1 (file-based routing, `routeTree.gen.ts` 자동 생성)을 사용한다.
- 데이터 페칭은 TanStack Query v5를 사용한다.
- 상태 관리는 Zustand v5를 사용한다.
- UI 프리미티브는 shadcn/ui (Radix 기반)를 사용한다.
- 차트는 Recharts v2를 사용한다.
- 스타일링은 Tailwind CSS v4를 사용한다.
- 현재 라우트: `/` (index), `/dashboard`, `/runs`, `/runs/$runId`, `/strategies`, `/patterns`, `/patterns/$patternSetId`, `/admin`
- 컴포넌트 구성: charts(3), dashboard(4), patterns(3), strategies(2), runs(4), shared(4), ui(8), layout(1)
- 백엔드 API 클라이언트: `frontend/src/api/` 하위에 client, types, backtests, dashboard, analytics, patterns, strategies, admin 모듈이 있다.
- 현재 디자인: 다크 테마(zinc-950 배경), 기본적인 Card 기반 레이아웃, 상태 처리가 일부 누락된 화면이 존재한다.

## Non-Goals

- 백엔드 API 변경 또는 신규 API 엔드포인트 추가
- 실시간 WebSocket/SSE 스트리밍 도입 (이번 phase에서는 polling 유지)
- 인증/인가 시스템 도입 (현재 API key 기반 유지)
- 모바일 네이티브 앱 또는 PWA 전환
- 새로운 차트 라이브러리 도입 (Recharts 유지)
- E2E 테스트 프레임워크 전면 도입 (Playwright 기본 smoke test만 포함)
- i18n/l10n 시스템 도입

## Hard Decisions

### D-1. Next.js App Router로 전환하되 API 호출은 클라이언트 사이드를 유지한다

- 트레이딩 시스템 백엔드는 별도 프로세스(`uvicorn`)로 실행되므로 Next.js 서버에서 직접 호출하는 것은 운영 복잡도를 높인다.
- 서버 컴포넌트는 레이아웃, 정적 콘텐츠, 페이지 쉘, 비인터랙티브 래퍼에만 사용한다. 데이터 기반 화면은 대부분 `use client` 경계 안에서 TanStack Query로 처리하며, 서버 컴포넌트에서 직접 데이터를 fetch하지 않는다.
- `loading.tsx`/`error.tsx`는 route-level fallback(초기 페이지 로드, JS 번들 로딩 중)으로 사용하고, query-level 상태(데이터 로딩/에러/빈 상태)는 각 클라이언트 컴포넌트 내부에서 TanStack Query의 `isLoading`/`isError` 등으로 처리한다.
- 향후 BFF(Backend-for-Frontend) 패턴이 필요해지면 Next.js Route Handlers로 확장할 수 있는 여지를 남긴다.

### D-1a. 기존 운영자 API 설정 UX를 보존한다

- 현재 프론트엔드는 `useApiStore`(Zustand persist)와 `ApiSettingsBar` 컴포넌트를 통해 운영자가 런타임에 base URL과 API key를 변경할 수 있다.
- `requestJson()`은 환경변수가 아니라 이 Zustand store에서 `baseUrl`/`apiKey`를 읽는 구조다.
- `NEXT_PUBLIC_API_BASE_URL`은 store의 초기 기본값으로만 사용하고, 운영자 override UI는 그대로 유지한다.
- `store/apiStore.ts`와 `components/shared/ApiSettingsBar.tsx`를 Step 0에서 명시적으로 이식한다.

### D-2. TanStack Router를 제거하고 Next.js 파일 기반 라우팅으로 전환한다

- TanStack Router와 Next.js App Router는 역할이 중복된다.
- `routeTree.gen.ts` 자동 생성과 `createFileRoute` 패턴을 Next.js `app/` 디렉토리 구조로 1:1 매핑한다.
- 마이그레이션 중 기존 라우트 구조를 보존한다.

### D-3. 디자인 시스템은 기존 shadcn/ui를 확장하는 방식으로 구성한다

- 새로운 UI 라이브러리를 도입하지 않는다.
- shadcn/ui 기본 컴포넌트 위에 트레이딩 도메인 전용 복합 컴포넌트(MetricCard, DataTable, StatusIndicator 등)를 계층화한다.
- 디자인 토큰(색상, 간격, 타이포그래피)을 Tailwind CSS 설정으로 중앙화한다.

### D-4. 점진적 마이그레이션이 아닌 클린 재구축을 선택한다

- 현재 SPA 규모(~55개 소스 파일)는 점진적 마이그레이션의 복잡도 대비 이점이 적다.
- `frontend-next/` 디렉토리에 새로 구축하고, 완성 후 `frontend/`를 교체한다.
- 기존 API 클라이언트 코드, 타입 정의, 유틸리티는 최대한 재활용한다.

### D-5. 프론트엔드 빌드와 배포는 백엔드와 독립적으로 유지한다

- Next.js는 standalone 빌드로 독립 실행하거나, `next export` static output으로 기존 방식을 유지할 수 있다.
- 이번 phase에서는 개발 서버(`next dev`) + 프로덕션 빌드(`next build`)까지만 검증한다.

## Product Requirements

### PR-1. Next.js App Router 기반 프로젝트 구조 수립

- `frontend-next/` 디렉토리에 Next.js 15 + App Router + TypeScript + Tailwind CSS v4 프로젝트를 생성한다.
- `app/` 디렉토리 구조가 현재 라우트(`/`, `/dashboard`, `/runs`, `/runs/[runId]`, `/strategies`, `/patterns`, `/patterns/[patternSetId]`, `/admin`)를 모두 포함해야 한다.
- 루트 레이아웃에 글로벌 네비게이션, 테마 설정, 쿼리 프로바이더를 포함해야 한다.
- 각 라우트에 route-level fallback용 `loading.tsx`와 `error.tsx`를 포함해야 한다.
- 기존 운영자 설정 UX(`ApiSettingsBar` + `apiStore`)를 루트 레이아웃에 포함해야 한다.

### PR-2. 디자인 시스템 및 토큰 정의

- Tailwind CSS 설정에 트레이딩 시스템 전용 디자인 토큰을 정의한다.
  - 색상 팔레트: 다크 테마 기반, 시맨틱 색상(success, danger, warning, info, muted)
  - 타이포그래피: 제목/본문/캡션/숫자 전용 타입 스케일
  - 간격: 4px 기반 시스템 (compact/default/relaxed density)
  - 차트 색상 팔레트
- shadcn/ui 컴포넌트의 테마를 디자인 토큰에 맞게 커스터마이즈한다.

### PR-3. 도메인 전용 복합 컴포넌트 구축

- 트레이딩 시스템에 특화된 재사용 가능 컴포넌트를 구축한다.
  - `MetricCard`: 숫자 지표 + 추세 표시 + 비교 값
  - `DataTable`: 정렬, 필터, 페이지네이션, 빈 상태를 지원하는 범용 데이터 테이블
  - `StatusIndicator`: 실시간 상태 표시 (online/offline/warning/error)
  - `ChartContainer`: 로딩/빈 상태를 포함하는 차트 래퍼
  - `PageHeader`: 제목 + 설명 + 액션 버튼 영역을 포함하는 페이지 헤더
- 모든 복합 컴포넌트는 loading, empty, error 상태를 지원해야 한다.

### PR-4. 대시보드 페이지 고도화

- 현재 3개 Card(Runtime Status, Positions & Cash, Recent Events) 구조를 운영자 친화적 레이아웃으로 재설계한다.
  - 상단: 핵심 지표 요약 (총 자산, 일간 손익, 포지션 수, 시스템 상태) → MetricCard 그리드
  - 중단: 포지션 테이블 + 포트폴리오 차트 → 2컬럼 레이아웃
  - 하단: 이벤트 피드 + 시스템 로그 → 타임라인 뷰
- 대시보드 제어 버튼(pause/resume/reset)은 페이지 헤더 영역에 통합한다.
- 연결 상태(live loop 활성 여부)를 상시 표시한다.

### PR-5. 백테스트 결과 뷰어 고도화

- `/runs` 목록 페이지: 실행 이력 테이블 + 필터 + 요약 통계
- `/runs/[runId]` 상세 페이지: 탭 기반 구조
  - Summary 탭: 핵심 지표 그리드 + 수익률 차트
  - Equity 탭: 자산 곡선 + 드로우다운 오버레이
  - Trades 탭: 거래 내역 테이블 + 산점도
  - Signals 탭: 시그널 이벤트 테이블
- 차트는 Recharts를 유지하되 ChartContainer로 감싸서 상태 처리를 통일한다.

### PR-6. 전략/패턴 관리 페이지 고도화

- `/strategies`: 전략 목록 + 생성/편집 폼을 개선한다.
- `/patterns`: 패턴 세트 목록 + 학습 폼 + 미리보기 테이블을 개선한다.
- 폼은 react-hook-form + zod 패턴을 유지하되, 필드 레벨 검증 피드백을 강화한다.

### PR-7. 반응형 디자인 및 접근성 기준 충족

- 모든 페이지가 mobile(375px), tablet(768px), desktop(1280px) breakpoint에서 의도적으로 동작해야 한다.
- 키보드 네비게이션으로 모든 인터랙티브 요소에 접근 가능해야 한다.
- 시맨틱 HTML을 우선 사용하고, ARIA 레이블을 적절히 부여해야 한다.

### PR-8. 개발자 경험 및 빌드 검증

- `next dev`로 로컬 개발이 가능해야 한다.
- `next build`가 에러 없이 완료되어야 한다.
- ESLint + TypeScript 타입 체크가 통과해야 한다.
- Playwright smoke test는 MSW(Mock Service Worker) 기반 mock API 위에서 실행한다. 실 백엔드 의존 없이 CI/로컬에서 재현 가능해야 한다.
- `package.json`에 `test:e2e` 스크립트를 정의하여 한 명령으로 smoke test를 실행할 수 있어야 한다.

## Scope By Epic

### Epic A. Next.js 프로젝트 부트스트랩 및 라우팅 마이그레이션

목표:
- `frontend-next/`에 Next.js App Router 프로젝트를 생성하고 기존 라우트를 모두 매핑한다.

포함:
- Next.js 15 프로젝트 초기화 (App Router, TypeScript, Tailwind CSS v4)
- `app/` 디렉토리에 기존 8개 라우트 매핑
- 루트 레이아웃 + 글로벌 네비게이션
- TanStack Query 프로바이더 설정
- 기존 API 클라이언트/타입 코드 이식
- 각 라우트별 `loading.tsx`, `error.tsx`

제외:
- 기존 TanStack Router 코드 유지보수
- SSR 데이터 페칭 (클라이언트 사이드 유지)

### Epic B. 디자인 시스템 구축

목표:
- 트레이딩 시스템 전용 디자인 토큰과 도메인 복합 컴포넌트를 정의한다.

포함:
- Tailwind 설정에 디자인 토큰 정의 (색상, 타이포그래피, 간격)
- shadcn/ui 테마 커스터마이즈
- MetricCard, DataTable, StatusIndicator, ChartContainer, PageHeader 구현
- 컴포넌트별 loading/empty/error 상태
- 다크 테마 기본

제외:
- 라이트 테마 지원
- 디자인 토큰 문서 사이트 (Storybook 등)

### Epic C. 대시보드 재설계

목표:
- 라이브 대시보드를 운영자 친화적 레이아웃으로 고도화한다.

포함:
- 지표 요약 그리드, 포지션 테이블, 포트폴리오 차트, 이벤트 피드
- 대시보드 제어 버튼 통합
- 연결 상태 표시
- 폴링 기반 데이터 갱신 유지

제외:
- WebSocket/SSE 실시간 스트리밍
- 대시보드 커스터마이즈(위젯 드래그 등)

### Epic D. 백테스트/전략/패턴 페이지 고도화

목표:
- 분석 및 관리 페이지를 탭/필터 기반 구조로 개선한다.

포함:
- `/runs` 목록 + 필터
- `/runs/[runId]` 탭 기반 상세 뷰
- `/strategies` 목록 + 폼 개선
- `/patterns` 목록 + 학습 폼 + 미리보기 개선
- `/admin` 페이지 정리

제외:
- 실시간 백테스트 진행 표시
- 전략 비교 뷰

### Epic E. 반응형/접근성/빌드 검증

목표:
- 반응형 디자인, 접근성, 빌드 파이프라인을 검증한다.

포함:
- 3개 breakpoint 반응형 검증
- 키보드 네비게이션 및 시맨틱 HTML 검증
- `next build` 성공 확인
- ESLint + TypeScript 타입 체크 통과
- Playwright smoke test (홈, 대시보드, 백테스트 목록)

제외:
- 전체 E2E 테스트 커버리지
- CI/CD 파이프라인 구축

## Impacted Files

### 신규 생성 (frontend-next/)
- `frontend-next/package.json`
- `frontend-next/next.config.ts`
- `frontend-next/tsconfig.json`
- `frontend-next/tailwind.config.ts`
- `frontend-next/components.json` (shadcn/ui 설정)
- `frontend-next/.env.local.example` (환경변수 예시)
- `frontend-next/app/layout.tsx`
- `frontend-next/app/page.tsx`
- `frontend-next/app/dashboard/page.tsx`
- `frontend-next/app/runs/page.tsx`
- `frontend-next/app/runs/[runId]/page.tsx`
- `frontend-next/app/strategies/page.tsx`
- `frontend-next/app/patterns/page.tsx`
- `frontend-next/app/patterns/[patternSetId]/page.tsx`
- `frontend-next/app/admin/page.tsx`
- `frontend-next/components/` (도메인 및 UI 컴포넌트)
- `frontend-next/lib/` (API 클라이언트, 유틸리티)
- `frontend-next/store/apiStore.ts` (Zustand 기반 API 설정 store)
- `frontend-next/components/shared/ApiSettingsBar.tsx` (운영자 API 설정 UI)

### 기존 참조 (이식 대상 — 변경 없음)
- `frontend/src/api/` (API 클라이언트 코드)
- `frontend/src/store/apiStore.ts` (Zustand store)
- `frontend/src/components/shared/ApiSettingsBar.tsx` (API 설정 바)
- `frontend/src/lib/formatters.ts`, `frontend/src/lib/strategyParser.ts`, `frontend/src/lib/patternParser.ts` (파서/포매터 유틸)
- `frontend/src/components/` (기존 컴포넌트 — 참고 대상)

### 문서
- `README.md` (프론트엔드 섹션 갱신)
- `prd/phase_7_prd.md`
- `prd/phase_7_implementation_plan.md`
- `prd/phase_7_task.md`

## Delivery Slices

### Slice 0. Next.js 프로젝트 부트스트랩

- `frontend-next/` 프로젝트 초기화
- 디자인 토큰 정의
- 루트 레이아웃 + 네비게이션

### Slice 1. 디자인 시스템 컴포넌트

- MetricCard, DataTable, StatusIndicator, ChartContainer, PageHeader 구현
- shadcn/ui 테마 커스터마이즈

### Slice 2. 대시보드 재설계

- 대시보드 페이지 레이아웃 재구축
- 폴링 훅 이식
- 제어 버튼 + 상태 표시 통합

### Slice 3. 백테스트/전략/패턴 페이지

- `/runs` 목록 + 상세 탭 뷰
- `/strategies`, `/patterns` 폼 개선
- 차트 컴포넌트 이식

### Slice 4. 반응형/접근성/빌드 검증

- 반응형 검증 및 조정
- 접근성 검증
- `next build` + lint + type check 통과
- Playwright smoke test

### Slice 5. 최종 교체 및 문서 정리

- `frontend-next/` → `frontend/` 교체
- 교체 시 자산 완전성 확인: `components.json`, `package-lock.json`, `.env.local.example`, parser 유틸(`formatters.ts`, `strategyParser.ts`, `patternParser.ts`), `store/apiStore.ts`, path alias 설정
- README 갱신
- 기존 Vite 설정 제거

## Success Metrics

- `frontend-next/`에서 `next build`가 에러 없이 완료될 것
- 기존 8개 라우트가 모두 Next.js App Router에서 동작할 것
- 모든 데이터 기반 화면에 loading, empty, error 상태가 존재할 것
- 대시보드가 MetricCard 그리드 + 2컬럼 레이아웃 + 타임라인 이벤트 피드 구조를 가질 것
- 375px, 768px, 1280px breakpoint에서 의도적 반응형 동작이 확인될 것
- Playwright smoke test가 홈, 대시보드, 백테스트 목록 페이지에서 통과할 것
- ESLint + TypeScript 타입 체크가 통과할 것

## Risks and Follow-up

- Next.js와 기존 FastAPI 백엔드 간 CORS 설정이 개발/프로덕션 환경에서 다르게 동작할 수 있다. `next.config.ts`에서 rewrites 또는 환경별 API base URL 설정이 필요할 수 있다.
- TanStack Query의 서버 컴포넌트 호환성(hydration, prefetching)은 이번 phase에서는 클라이언트 사이드로 유지하지만, 향후 RSC 데이터 페칭 패턴으로 전환할 여지를 남겨야 한다.
- Recharts는 클라이언트 전용이므로 차트를 포함하는 모든 컴포넌트는 `use client` 경계가 필요하다.
- 기존 `frontend/` 교체 시점에 운영 중인 대시보드 사용자에게 영향이 있을 수 있다. 교체 전 smoke test 완료 필수.
- Playwright 테스트는 백엔드 mock 또는 실행 중인 백엔드를 전제하므로, 테스트 환경 구성이 필요하다.
- 향후 WebSocket/SSE 도입, 인증 시스템, 라이트 테마 등은 Phase 8 이후 범위로 남는다.
