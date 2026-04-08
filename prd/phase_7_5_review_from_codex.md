# Phase 7.5 Review From Codex

검토 일자: 2026-04-07

검토 대상:
- `prd/phase_7_5_prd.md`
- `prd/phase_7_5_implementation_plan.md`
- `prd/phase_7_5_task.md`
- 현재 워크트리의 `frontend/` 변경사항

## Overall Verdict

현재 변경사항은 **Phase 7.5의 핵심 사용자 가시 기능 일부를 실제로 구현했다.**

- dashboard equity chart는 placeholder에서 실제 차트로 교체되었다.
- `/runs/[runId]`는 탭 기반 레이아웃으로 전환되었다.
- Playwright smoke test 3개는 실제 실행에서 통과했다.

하지만 계획 문서 기준으로는 **완료 판정을 주기 어렵다.**

주요 이유:
- Playwright 하네스가 계획된 `MSW` 기반이 아니라 `page.route()` 기반으로 구현되었다.
- `npm run lint`가 `frontend/test-results` 산출물 때문에 실패한다.
- `RunDetailTabs`는 요구한 상태 관리/empty-state 세부사항을 모두 충족하지 않는다.
- Dashboard equity chart의 B1 go/no-go 판단은 코드에는 반영되었지만 문서화된 판정 증적이 없다.

따라서 현재 상태 평가는 다음이 적절하다.

> Phase 7.5는 A3, B2, B3, C1, C3는 검증 가능 수준으로 구현되었지만,
> A1, A2, B1, C2, D는 계획 기준으로 아직 닫히지 않았다.

## Verified Evidence

실행 확인:
- `cd frontend && npx tsc --noEmit` → PASS
- `cd frontend && npm run build` → PASS
- `cd frontend && npm run test:e2e` → PASS, `3 passed (2.6s)`
- `cd frontend && npm run lint` → FAIL

빌드/테스트가 샌드박스 밖에서 재실행된 이유:
- 기본 샌드박스에서는 Next.js/Turbopack가 프로세스/포트 제약으로 실패했다.
- 권한 확장 후 `build`, `test:e2e`는 정상 통과했다.

## Findings

### 1. Playwright 하네스는 통과하지만, 계획된 `MSW` 구현은 아니다

근거:
- `frontend/package.json`에 `@playwright/test`, `msw`, `test:e2e`는 추가됨
- `frontend/playwright.config.ts` 존재
- `frontend/e2e/smoke.spec.ts` 존재 및 3개 smoke test 통과
- 그러나 `frontend/e2e/mocks/setup.ts`는 Service Worker 초기화가 아니라 `page.route()` 래퍼 re-export만 수행함
- `frontend/public/`에 `mockServiceWorker.js`가 없음

세부 근거:
- `frontend/e2e/mocks/handlers.ts:113-141`는 Playwright `page.route()`로만 mock 처리
- `frontend/e2e/mocks/setup.ts:1-11`는 MSW worker 초기화 없이 route mocking 선택을 명시
- `frontend/playwright.config.ts:11-16`는 `next build && npm start` 기반 서버 기동

판단:
- A3 자체는 완료로 볼 수 있다.
- 하지만 A1/A2의 “MSW Service Worker 기반 하네스”라는 원래 계획은 충족되지 않았다.
- 현재 구현은 PRD의 fallback을 실제 기본 전략으로 채택한 상태다.

결론:
- **동작하는 e2e smoke test는 확보되었지만, `Playwright + MSW` 완료라고 체크하면 과장이다.**

### 2. `tsc --noEmit`는 e2e 코드를 실제로 검증하지 않는다

근거:
- `frontend/tsconfig.json:28`에서 `"e2e"`가 exclude 되어 있다.
- 동시에 task 문서는 Step A2에서 “`tsc --noEmit` 통과 확인 (e2e 포함)”을 요구한다.

판단:
- 현재 `npx tsc --noEmit` PASS는 앱 코드 기준이다.
- `frontend/e2e/`의 타입 안정성은 그 명령으로 증명되지 않는다.

결론:
- **A2의 exit criteria는 아직 충족되지 않았다.**

### 3. Dashboard equity chart는 구현되었지만 B1 gate는 문서 증적이 부족하다

근거:
- `frontend/components/dashboard/EquityChart.tsx:1-58` 신규 구현
- `frontend/app/dashboard/page.tsx:41-47`에서 placeholder를 실제 차트로 교체
- `frontend/hooks/useDashboardPolling.ts:9-17`에서 `cash + quantity * average_cost + unrealized_pnl` 기반 portfolio value 파생
- `frontend/hooks/useDashboardPolling.ts:58-75`에서 polling 결과를 누적 시계열로 유지

판단:
- B2/B3 구현은 실제로 존재하고 build도 통과한다.
- 다만 B1에서 요구한 “Go/No-Go 판정”과 “공식 문서화”는 코드 외 별도 증적이 없다.
- 즉 구현은 되었지만, 계획 문서가 요구한 decision gate는 닫히지 않았다.

결론:
- **B2/B3는 완료로 볼 수 있으나, B1은 미완료로 남기는 것이 맞다.**

### 4. `RunDetailTabs`는 큰 방향은 맞지만 C2 세부 요구를 모두 충족하지 않는다

근거:
- `frontend/components/runs/RunDetailTabs.tsx:27-33`에서 4개 탭 구성
- `frontend/app/runs/[runId]/page.tsx:44-54`에서 페이지가 `RunDetailTabs`를 사용하도록 전환
- `frontend/components/ui/tabs.tsx`는 기존 래퍼를 그대로 재사용

미충족 또는 애매한 부분:
- `frontend/components/runs/RunDetailTabs.tsx:27`은 `defaultValue="summary"`만 사용하고, task 문서가 명시한 `useState` 기반 로컬 상태 관리는 없다.
- `frontend/components/runs/RunDetailTabs.tsx:63-72`에서 analytics unavailable일 때 Charts 탭 전체 empty state가 아니라 equity/drawdown은 그대로 렌더링하고 scatter만 안내 문구를 표시한다.
- `frontend/components/runs/RunDetailTabs.tsx:76-87`에서 Trades 탭은 analytics 없을 때 `TradesTable` 대신 `FillsTable`만 보여 주므로 “Trades 탭: TradesTable + FillsTable” 요구를 완전히 만족했다고 보긴 어렵다.

판단:
- C3 전환 자체는 완료다.
- C2는 “대체로 구현”이지만, 계획 문서 기준으로는 부분 완료다.

결론:
- **C1, C3는 체크 가능하지만 C2는 보류가 안전하다.**

### 5. 최종 검증 Step D는 닫히지 않았다

근거:
- `npm run lint` 실행 시 다음 오류 발생:
  - `Error: ENOENT: no such file or directory, scandir '/home/roqkf/trading_system/frontend/test-results'`
- `frontend/eslint.config.mjs:5-15`의 ignore 설정에는 `test-results/**`가 없다.
- `frontend/test-results/.last-run.json`이 실제 생성되어 있다.

판단:
- Playwright 실행 산출물이 lint 대상에 포함되면서 검증 순서에 따라 lint가 깨진다.
- 이는 Step D의 `npm run lint` PASS 요구를 직접 위반한다.

결론:
- **최종 검증 완료로 체크할 수 없다.**

## Step-by-Step Judgment

### 체크 가능

- Step 7.5-A3
  - `frontend/e2e/smoke.spec.ts` 작성됨
  - `npm run test:e2e` 실제 통과
- Step 7.5-B2
  - `frontend/components/dashboard/EquityChart.tsx` 구현됨
  - `useDashboardPolling`에 equity 파생 로직 추가됨
- Step 7.5-B3
  - `frontend/app/dashboard/page.tsx`에서 placeholder 제거 및 실제 차트 렌더링 확인
  - `npm run build` PASS
- Step 7.5-C1
  - `frontend/components/ui/tabs.tsx` 재사용으로 인터페이스 적합성 사실상 입증
- Step 7.5-C3
  - `frontend/app/runs/[runId]/page.tsx`가 `RunDetailTabs` 기반으로 전환됨
  - `npm run build` PASS

### 체크 보류

- Step 7.5-A1
  - Playwright 의존성과 config는 있으나 `mockServiceWorker.js`가 없고 MSW 초기화 경로가 없다
- Step 7.5-A2
  - 실제 구현은 `page.route()` 기반이며 MSW handler/setup이 아니다
  - `tsc --noEmit`도 `e2e`를 제외하고 있어 exit criteria 미충족
- Step 7.5-B1
  - 파생 공식은 코드에 있으나 go/no-go gate 문서화 증적이 없다
- Step 7.5-C2
  - 탭 컴포넌트는 구현되었지만 상태 관리와 empty-state 세부 요구가 일부 다르다
- Step 7.5-D
  - `lint` 실패로 최종 검증 완료 불가

## Recommended Follow-up

1. e2e 전략을 문서에 맞출지, 구현을 기준으로 문서를 수정할지 결정해야 한다.
   - 문서 유지 시: 실제 MSW browser worker 도입 및 `mockServiceWorker.js` 생성
   - 구현 유지 시: PRD/계획/태스크에서 `page.route()`를 기본 전략으로 승격

2. `frontend/eslint.config.mjs` 또는 ignore 정책에 `test-results/**`를 추가해야 한다.
   - 그렇지 않으면 Playwright를 한 번 돌린 뒤 lint가 깨지는 회귀가 계속 남는다.

3. `frontend/tsconfig.json`에서 e2e 타입 검증 정책을 명확히 해야 한다.
   - e2e를 계속 제외할 것이면 task 문서의 exit criteria를 고쳐야 한다.
   - task 문서를 유지할 것이면 e2e용 tsconfig 또는 포함 설정이 필요하다.

4. `RunDetailTabs`의 완료 기준을 좁혀 다시 맞추는 편이 좋다.
   - `useState` 기반 탭 상태가 정말 필요한지 결정
   - analytics unavailable 시 Charts/Trades 탭의 기대 표시 상태를 문서와 구현 중 하나로 통일

## Files Reviewed

- `frontend/package.json`
- `frontend/playwright.config.ts`
- `frontend/e2e/mocks/handlers.ts`
- `frontend/e2e/mocks/setup.ts`
- `frontend/e2e/smoke.spec.ts`
- `frontend/eslint.config.mjs`
- `frontend/tsconfig.json`
- `frontend/app/dashboard/page.tsx`
- `frontend/hooks/useDashboardPolling.ts`
- `frontend/components/dashboard/EquityChart.tsx`
- `frontend/app/runs/[runId]/page.tsx`
- `frontend/components/runs/RunDetailTabs.tsx`
