# Phase 7 Review From Codex

## Verdict (v2)

Phase 7은 **실질적으로 많이 구현되었고 Next.js/App Router 전환도 성공했으며, 후속 수정으로 lint/form/README/task evidence도 보강되었다.** 다만 `prd/phase_7_prd.md` 기준으로는 아직 “완료 승인” 상태는 아니다.

가장 중요한 이유는 다음 세 가지다.

1. Next.js App Router 전환과 주요 화면 이식은 실제로 반영되었다.
2. 후속 수정으로 lint gate, `react-hook-form + zod`, `frontend/README.md`, `phase_7_task.md` 실행 증적은 실제로 반영되었다.
3. 그러나 Playwright/MSW smoke test, dashboard equity chart, `/runs/[runId]` 탭 기반 UX 같은 일부 open item은 여전히 남아 있다.

즉, 현재 상태는 **"architecture migration largely landed and several follow-up fixes are verified, but completion sign-off is not supported yet"**로 판단한다.

---

## 1. Clearly achieved

### 1.1 Next.js App Router 전환은 실제로 이루어졌다

근거:
- `frontend/package.json`
- `frontend/app/layout.tsx`
- `frontend/app/page.tsx`
- `frontend/app/dashboard/page.tsx`
- `frontend/app/runs/page.tsx`
- `frontend/app/runs/[runId]/page.tsx`
- `frontend/app/strategies/page.tsx`
- `frontend/app/patterns/page.tsx`
- `frontend/app/patterns/[patternSetId]/page.tsx`
- `frontend/app/admin/page.tsx`

확인 사항:
- 활성 프론트엔드는 더 이상 Vite + TanStack Router SPA 구조가 아니다.
- `app/` 디렉토리와 route-level `loading.tsx` / `error.tsx` 파일이 존재한다.
- `next build`가 실제로 통과했다.

### 1.2 운영자 API 설정 UX는 보존되었다

근거:
- `frontend/store/apiStore.ts`
- `frontend/components/shared/ApiSettingsBar.tsx`
- `frontend/lib/api/client.ts`
- `frontend/app/layout.tsx`

확인 사항:
- `requestJson()`은 여전히 Zustand store에서 `baseUrl`/`apiKey`를 읽는다.
- `ApiSettingsBar`도 루트 레이아웃에 포함되어 있다.
- PRD의 D-1a 요구사항은 대체로 충족된 것으로 본다.

### 1.3 핵심 이식 자산은 상당수 반영되었다

근거:
- `frontend/lib/api/*`
- `frontend/lib/queryClient.ts`
- `frontend/lib/utils.ts`
- `frontend/lib/formatters.ts`
- `frontend/lib/strategyParser.ts`
- `frontend/lib/patternParser.ts`
- `frontend/components/domain/*`
- `frontend/components/layout/PageHeader.tsx`
- `frontend/components/layout/NavBar.tsx`
- `frontend/components/charts/*`
- `frontend/components.json`
- `frontend/.env.local.example`

---

## 2. Partially achieved

### 2.1 디자인 시스템과 도메인 컴포넌트는 들어왔지만 PRD 수준의 완성도는 아니다

근거:
- `frontend/components/domain/MetricCard.tsx`
- `frontend/components/domain/DataTable.tsx`
- `frontend/components/domain/StatusIndicator.tsx`
- `frontend/components/domain/ChartContainer.tsx`
- `frontend/components/layout/PageHeader.tsx`

판단:
- PRD가 요구한 도메인 복합 컴포넌트들은 대체로 존재한다.
- 하지만 `DataTable`은 PRD에 적힌 정렬/필터/페이지네이션 완성도까지 확인되지 않는다.
- 일부 컴포넌트는 loading/empty 지원은 있으나 error/empty API가 통일적으로 설계된 수준은 아니다.

### 2.2 대시보드 재설계는 부분 구현이다

근거:
- `frontend/app/dashboard/page.tsx`
- `frontend/components/dashboard/DashboardMetrics.tsx`
- `frontend/components/dashboard/PositionsPanel.tsx`
- `frontend/components/dashboard/EventTimeline.tsx`
- `frontend/hooks/useDashboardPolling.ts`

판단:
- MetricCard 그리드, 제어 버튼, 상태 표시, 이벤트 타임라인은 존재한다.
- 그러나 PRD가 기대한 포트폴리오 차트 영역은 실제 차트 컴포넌트가 아니라 placeholder에 가깝다.
  - `frontend/app/dashboard/page.tsx`에서 `ChartContainer`가 `empty={true}`와 `{null}`로 렌더링된다.
- 따라서 Slice 2를 “완료”로 보기는 어렵고, **부분 달성**으로 본다.

### 2.3 runs/strategies/patterns/admin은 이식되었고, 특히 `/runs/[runId]`는 기능적으로 높은 진척도를 보인다

근거:
- `frontend/app/runs/page.tsx`
- `frontend/app/runs/[runId]/page.tsx`
- `frontend/app/strategies/page.tsx`
- `frontend/app/patterns/page.tsx`
- `frontend/app/patterns/[patternSetId]/page.tsx`
- `frontend/app/admin/page.tsx`
- `frontend/components/strategies/StrategyForm.tsx`
- `frontend/components/patterns/PatternTrainForm.tsx`

판단:
- 페이지와 API 연동은 실제로 존재한다.
- `/runs/[runId]`는 실제 차트(`EquityCurveChart`, `DrawdownChart`, `TradeScatterChart`), analytics 연동, signals/fills/trades 테이블, summary grid를 갖추고 있어 **기능 커버리지는 높다.**
- 다만 PRD가 요구한 **탭 기반 구조**가 아니라 카드 나열 구조이므로, 명세와 UX 구조는 일치하지 않는다.
- 전략/패턴 폼은 동작 가능한 수동 폼이지만, PRD가 못 박은 `react-hook-form + zod` 패턴은 사용하지 않았다.
- 따라서 Slice 3은 **기능적으로는 상당 부분 달성되었으나, 일부 명시 스펙 기준으로는 부분 달성**으로 본다.

---

## 3. Clearly missing or blocking

### 3.1 lint 게이트는 후속 수정으로 닫혔다

근거:
- `frontend/hooks/useDashboardPolling.ts:38`
- `prd/phase_7_task.md:153-166`
- 후속 검증에서 `npm run lint` 통과 확인

변경:
- 기존 `useState(Date.now())`는 `useState(() => Date.now())`로 수정되었다.

영향:
- PRD의 PR-8 / Step 4 / Success Metrics 중 lint 항목은 현재 충족된 것으로 본다.
- 이 항목은 더 이상 open blocker가 아니다.

### 3.2 Playwright + MSW smoke test 요구사항이 구현되지 않았다

근거:
- `frontend/e2e/` 없음
- Playwright config 없음
- `package.json`에 `test:e2e` 없음
- `msw` 관련 파일/참조 없음

영향:
- PRD의 PR-8, Phase 7-4 checklist, Validation Matrix를 직접적으로 미충족한다.

### 3.3 `react-hook-form + zod` 요구사항은 후속 수정으로 반영되었다

근거:
- `frontend/package.json`
- `frontend/components/strategies/StrategyForm.tsx`
- `frontend/components/patterns/PatternTrainForm.tsx`

변경:
- `react-hook-form`, `zod`, `@hookform/resolvers` 의존성이 추가되었다.
- `StrategyForm`은 `useForm`, `Controller`, `zodResolver` 기반으로 전환되었다.
- `PatternTrainForm`도 `useForm` + `zodResolver` 기반으로 전환되었다.

영향:
- PRD의 PR-6 요구사항은 현재 대체로 충족된 것으로 본다.
- 이 항목은 더 이상 open blocker가 아니다.

### 3.4 실행 추적 문서는 후속 수정으로 상당 부분 정리되었다

근거:
- `prd/phase_7_task.md`

문제:
- Steps 0~3은 완료 상태로 정리되었다.
- Steps 4~5는 partial 상태와 미구현 항목이 분리 기록되었다.
- `Execution Log`에 2026-04-05 후속 수정 내용이 추가되었다.

영향:
- 이전과 달리 저장소 기준의 완료 증적은 상당 부분 보강되었다.
- 다만 문서 자체도 Playwright/MSW, dashboard equity chart, 탭 UX 차이를 open item으로 남기고 있어, "partial closure" 상태로 보는 것이 정확하다.

### 3.5 문서 정리는 일부 보강되었지만 완전히 닫히지는 않았다

근거:
- `frontend/README.md`
- `prd/phase_7_task.md`

영향:
- `frontend/README.md`는 실제 Next.js/App Router 프로젝트 문서로 재작성되었다.
- 다만 root `README.md`까지 포함한 phase-level 문서 sync가 완전히 닫혔다고 보기는 어렵다.

---

## 4. PRD와 실제 구현의 구조적 불일치

### 4.1 `frontend-next/` 기반 단계적 교체 계획과 실제 디스크 상태가 다르다

근거:
- `prd/phase_7_prd.md`
- `prd/phase_7_implementation_plan.md`
- `prd/phase_7_task.md`
- 실제 디스크에는 `frontend-next/` 없음
- 실제 활성 앱은 `frontend/`

판단:
- 최종적으로 `frontend/`가 Next.js 앱인 점 자체는 문제가 아니다.
- 다만 PRD/task/plan은 여전히 `frontend-next/` 빌드 후 교체 흐름을 기준으로 적혀 있어서, **실제 구현 경로와 문서가 어긋난다.**

### 4.2 현재 baseline 문구가 이미 실제 상태와 다를 가능성이 높다

근거:
- `prd/phase_7_prd.md:36-46`

판단:
- PRD는 현재 baseline을 Vite + TanStack Router SPA로 적고 있지만, 실제 저장소는 이미 Next App Router 구조다.
- 이는 “PRD가 구현 후에도 갱신되지 않았거나, 구현이 문서와 다른 절차로 진행되었다”는 뜻이다.

---

## 5. Final judgment

### 목적 적합성 판단

Phase 7의 원래 목적은 다음 두 가지였다.

1. 프론트엔드를 Next.js App Router 기반 프로덕션 프론트엔드로 전환
2. 디자인 시스템, 상태 커버리지, 검증 체계를 포함한 운영 적합성 확보

이 기준에서 보면:

- **목적 1 (아키텍처 전환)**: 대체로 달성
- **목적 2 (운영 적합성 + 검증 + 문서 종료)**: 부분 달성이나 아직 완료 승인 전

### 최종 판정

**Phase 7은 substantially implemented 상태이며, 후속 수정으로 이전 review의 핵심 blocker 상당수가 해소되었다. 하지만 `implemented properly and complete`로 최종 승인하기에는 아직 부족하다.**

가장 보수적이면서도 정확한 표현은 다음과 같다.

> Next.js/App Router 전환과 주요 화면 이식은 실질적으로 반영되었고,
> `/runs/[runId]` 같은 핵심 화면은 기능적으로 높은 진척도를 보이지만,
> 후속 수정으로 lint 통과, `react-hook-form + zod` 폼 패턴, `frontend/README.md`, `phase_7_task.md` 증적은 반영되었지만,
> Playwright/MSW smoke test, dashboard equity chart, `/runs/[runId]` 탭 기반 UX 같은 open item이 남아 있어
> 저장소 기준으로는 아직 완료 승인 상태가 아니다.

---

## 6. Suggested follow-up focus

1. Playwright + MSW + `test:e2e` 도입
2. dashboard live equity chart 구현
3. `/runs/[runId]` 탭 기반 UX 전환 여부 결정 및 반영
4. root README를 포함한 최종 문서 sync 검토

---

## 7. Post-review verification update (2026-04-05)

후속 수정 이후 다음 항목은 실제 파일과 검증 명령으로 재확인되었다.

- `frontend/hooks/useDashboardPolling.ts`는 `useState(() => Date.now())`로 수정됨
- `frontend/components/strategies/StrategyForm.tsx`는 `react-hook-form + zod + Controller + zodResolver` 적용
- `frontend/components/patterns/PatternTrainForm.tsx`는 `react-hook-form + zod + zodResolver` 적용
- `frontend/package.json`에 `react-hook-form`, `zod`, `@hookform/resolvers` 포함
- `frontend/README.md`는 Next.js/App Router 기준 프로젝트 문서로 재작성됨
- `prd/phase_7_task.md`는 Steps 0~3 완료, Steps 4~5 partial, execution log 반영 상태로 갱신됨
- `npx tsc --noEmit` 통과
- `npm run lint` 통과
- `npm run build` 통과

반면 아래 항목은 여전히 open 상태다.

- Playwright + MSW + `test:e2e` 미구현
- dashboard portfolio equity chart placeholder 유지
- `/runs/[runId]` 탭 기반 UX 미반영 (기능은 강하지만 PRD와 구조 차이 존재)
