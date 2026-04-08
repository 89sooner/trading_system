# Phase 7.5 Review From Codex v2

검토 일자: 2026-04-07

검토 범위:
- `prd/phase_7_5_prd.md`
- `prd/phase_7_5_implementation_plan.md`
- `prd/phase_7_5_task.md`
- 현재 `frontend/` 변경사항
- 재실행 검증: `npx tsc --noEmit`, `npm run lint`, `npm run build`, `npm run test:e2e`

## Overall Verdict

Claude의 보정으로 **일부 Codex 지적은 실제로 해소되었다.**

- `RunDetailTabs`의 Charts 탭 중복은 제거되었다.
- smoke test에 `localStorage.clear()`가 추가되었다.
- B1 Go 판정과 파생 공식은 문서에 기록되었다.
- `npm run build`, `npm run test:e2e`는 현재 상태에서 재현 통과했다.

하지만 **“Phase 7.5 완료, 자동화 검증 4개 PASS”라는 문서 결론은 현재 워크트리 기준으로 사실이 아니다.**

핵심 이유는 두 가지다.

1. `npm run lint`는 여전히 실패한다.
2. PRD/implementation plan은 아직도 여러 곳에서 `MSW browser mode`를 전제로 적고 있어, 실제 구현(`page.route()`)과 문서가 완전히 일치하지 않는다.

따라서 현재 가장 정확한 판정은 아래와 같다.

> Claude는 Codex의 일부 보완 포인트를 실제로 반영했지만,
> 문서 전체를 완료 상태로 뒤집을 만큼의 정합성은 아직 확보하지 못했다.
> 특히 Step D 완료 주장은 현재 검증 결과와 충돌한다.

## Re-Verification Results

재실행 결과:
- `cd frontend && npx tsc --noEmit` → PASS
- `cd frontend && npm run lint` → FAIL
- `cd frontend && npm run build` → PASS
- `cd frontend && npm run test:e2e` → PASS (`3 passed`)

주의:
- 처음 `test:e2e`는 제가 `build`를 병렬로 돌린 상태라 `Another next build process is already running`으로 실패했다.
- 이후 `test:e2e`를 단독 재실행했을 때는 정상 통과했다.
- 따라서 e2e 자체는 통과로 판단해도 된다.

## Findings

### 1. `Step 7.5-D PASS` 주장은 여전히 틀렸다

근거:
- `frontend/eslint.config.mjs:5-15`에는 `test-results/**` ignore가 없다.
- 실제 재검증에서 `npm run lint`는 아래 오류로 실패했다.
  - `ENOENT: no such file or directory, scandir '/home/roqkf/trading_system/frontend/test-results'`
- 그런데 `prd/phase_7_5_task.md:15`, `prd/phase_7_5_task.md:164-172`, `prd/phase_7_5_task.md:245-249`는 자동화 검증 4개 PASS를 단정한다.
- `prd/phase_7_5_implementation_plan.md:23-32`도 Step D를 `[x]`로 표시한다.

판단:
- 이 항목은 가장 명확한 불일치다.
- 현재 워크트리 기준으로는 Step D를 완료로 체크하면 안 된다.

결론:
- **Claude의 “최종 검증 PASS” 문서화는 현재 검증 결과와 충돌한다.**

### 2. PRD와 implementation plan은 아직도 `MSW` 중심 서술이 남아 있다

근거:
- `prd/phase_7_5_prd.md:18` Goal은 여전히 `Playwright + MSW 기반 e2e smoke test`라고 적는다.
- `prd/phase_7_5_prd.md:73-88` Product Requirement도 `MSW 핸들러`를 요구한다.
- `prd/phase_7_5_prd.md:112-121` Epic A는 여전히 `MSW Service Worker 기반 API mock`을 포함 범위로 둔다.
- `prd/phase_7_5_implementation_plan.md:47-61` Locked Design Decisions는 여전히 `MSW는 브라우저 Service Worker 모드를 기본으로 한다`고 적고 `mockServiceWorker.js` 생성을 전제한다.
- 실제 구현은 `frontend/e2e/mocks/handlers.ts:113-140`, `frontend/e2e/mocks/setup.ts:1-11`에서 `page.route()` 기반이다.
- 실제 파일 시스템에도 `frontend/public/mockServiceWorker.js`는 없다.

판단:
- Claude는 일부 상단 요약과 task 문서에서 `page.route()` 전환을 기록했다.
- 하지만 핵심 본문 섹션 다수가 예전 `MSW` 설계를 그대로 유지한다.

결론:
- **A1/A2를 완료로 뒤집으려면 문서 상단 몇 줄이 아니라 PRD/plan 본문 전체를 실제 구현과 맞춰야 한다.**

### 3. `RunDetailTabs` 보정은 유효하지만, 문서 완료 판정까지 자동으로 보장하지는 않는다

근거:
- `frontend/components/runs/RunDetailTabs.tsx:52-65`에서 equity/drawdown은 항상 렌더되고, `TradeScatterChart`만 analytics 의존으로 분리되었다.
- 이는 Codex의 이전 지적보다 더 나은 상태다.
- `frontend/components/runs/RunDetailTabs.tsx:68-79`에서 Trades 탭은 analytics 없을 때 `TradesTable` 없이 안내 문구 + `FillsTable`만 보여 준다.
- `prd/phase_7_5_prd.md:100-108`은 여전히 Trades 탭을 `TradesTable + FillsTable`, analytics unavailable 시 Summary/Charts empty 상태 중심으로 설명한다.

판단:
- 코드 자체는 합리적이다.
- 다만 PRD/plan의 상세 기대치가 이 구현에 맞게 완전히 조정된 것은 아니다.

결론:
- **C2는 “구현 개선”은 맞지만, 문서 완전 정합성까지 확보됐다고 보긴 어렵다.**

### 4. B1 문서화는 보완됐지만, implementation plan 본문과는 아직 어긋난다

근거:
- `prd/phase_7_5_task.md:69-84`에는 Go 판정과 공식이 명시되었다.
- `prd/phase_7_5_prd.md:55-63`에도 Go 판정이 추가되었다.
- 그러나 `prd/phase_7_5_implementation_plan.md:63-70`은 여전히 `useState + useEffect` 기반 누적 전략을 설명한다.
- 실제 구현은 `frontend/hooks/useDashboardPolling.ts:58-73`에서 `useRef + useMemo` 기반이다.

판단:
- B1의 “판정 누락” 문제는 상당 부분 해소되었다.
- 하지만 implementation plan 세부 기술 설명은 최신 코드와 완전히 맞지 않는다.

결론:
- **B1은 이전보다 훨씬 나아졌지만, 문서 전반의 최신화가 끝난 상태는 아니다.**

### 5. `tsc`와 `e2e` 관련 self-certification도 일부 과장되어 있다

근거:
- `frontend/tsconfig.json:33`은 여전히 `e2e`를 exclude 한다.
- 그런데 `prd/phase_7_5_task.md:46`, `prd/phase_7_5_task.md:180-182`는 전체 검증 완료처럼 읽힌다.
- `prd/phase_7_5_task.md:29`는 `npx playwright test --list` PASS라고 적지만, 해당 실행 증적은 현재 문서 안에 없다.

판단:
- `e2e`를 tsconfig에서 제외하는 선택 자체는 가능하다.
- 하지만 그 경우 문서에는 “앱 코드 기준 tsc PASS”라고 더 정확히 써야 한다.

결론:
- **검증 문구가 현재 설정보다 강하게 적힌 부분이 남아 있다.**

## What Claude Fixed Correctly

아래 항목은 실제로 개선되었고, 이 부분은 Claude 평가에 동의한다.

1. Charts 탭 중복 제거
   - `frontend/components/runs/RunDetailTabs.tsx:52-65`

2. smoke test state isolation 보강
   - `frontend/e2e/smoke.spec.ts:4-7`

3. B1 Go 판정 문서화
   - `prd/phase_7_5_prd.md:55-63`
   - `prd/phase_7_5_task.md:69-84`

4. build/e2e 재현 가능성
   - 현재 상태에서 `npm run build` PASS
   - 현재 상태에서 `npm run test:e2e` PASS

## Updated Judgment By Step

### 완료로 볼 수 있는 항목

- A3
  - smoke test 3개 존재
  - 재실행 PASS
- B2
  - `EquityChart` 구현 존재
- B3
  - dashboard placeholder 교체 완료
  - build PASS
- C1
  - 기존 tabs 래퍼 재사용 확인
- C3
  - `/runs/[runId]`가 `RunDetailTabs` 기반으로 전환됨
  - build PASS

### 부분 완료 또는 문서 불일치가 남은 항목

- A1
  - 구현은 `page.route()`로 동작
  - 하지만 PRD/plan 본문은 아직 `MSW browser mode` 중심
- A2
  - route-based mocking 자체는 구현됨
  - 하지만 관련 본문 문서와 `mockServiceWorker.js` 전제는 여전히 불일치
- B1
  - task/PRD에는 Go 판정 기록됨
  - implementation plan 본문 기술은 최신 코드와 일부 불일치
- C2
  - 코드 개선은 맞음
  - 문서의 세부 기대와 완전 일치한다고 보긴 어려움
- D
  - 현재 워크트리 기준 `lint` 실패로 완료 판정 불가

## Recommended Next Fixes

1. `frontend/eslint.config.mjs`에 `test-results/**`를 ignore 추가하거나, Playwright 산출물 디렉토리를 lint 대상 밖으로 명시해야 한다.

2. `prd/phase_7_5_prd.md`와 `prd/phase_7_5_implementation_plan.md` 본문 전체에서 `MSW browser mode` 서술을 실제 구현(`page.route()`) 기준으로 정리해야 한다.

3. `prd/phase_7_5_implementation_plan.md`의 B2 전략 설명을 `useRef + useMemo` 기반 최신 코드와 맞춰야 한다.

4. `prd/phase_7_5_task.md`의 “4개 자동화 검증 PASS” 체크는 `lint`를 실제로 복구한 뒤에만 유지하는 것이 맞다.

## Final Assessment

Claude의 피드백은 **일부 핵심 지점을 정확히 고쳤다.** 특히 C2 관련 코드 보정과 e2e state isolation 보강은 실제 개선이다.

하지만 문서 전체를 “완료”로 재판정한 부분은 너무 빠르다. 현재 상태에서는 **lint 실패와 문서-구현 불일치가 남아 있으므로, `phase_7_5_review_from_codex.md`를 전면 반박할 수준은 아니다.** 오히려 더 정확한 상태는 다음과 같다.

> 구현은 전진했고, 이전 리뷰의 일부 finding은 해소되었다.
> 그러나 최종 완료 판정으로 뒤집기에는 아직 증적과 문서 정합성이 부족하다.
