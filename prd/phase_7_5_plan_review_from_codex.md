# Phase 7.5 Plan Review From Codex

## Overall verdict

`prd/phase_7_5_prd.md`, `prd/phase_7_5_implementation_plan.md`, `prd/phase_7_5_task.md`는 **방향 자체는 적절하다.**

특히 이 계획은 Phase 7 검토에서 남은 open item 3개를 정확히 겨냥하고 있고, 범위를 새 기능 확장으로 넓히지 않으려는 점이 좋다.

다만 현재 `frontend/` 코드 기준으로 보면, 이 계획은 **그대로 구현에 들어가기엔 몇 가지 전제가 과하게 낙관적**이다.

가장 큰 이슈는 두 가지다.

1. dashboard equity chart는 현재 API/타입 구조상 직접 그릴 근거가 약하다.
2. Playwright + MSW 계획은 `/runs` 페이지의 실제 데이터 경로와 완전히 맞지 않는다.

즉, 이 계획은 **폐기할 필요는 없지만, 구현 전 보정이 필요한 plan**이다.

---

## 1. 적절한 점

### 1.1 범위 설정이 정확하다

근거:
- `prd/phase_7_5_prd.md:12-20`
- `prd/phase_7_review_from_codex.md:236-249`

판단:
- Phase 7 검토에서 남은 핵심 3개 항목만 좁게 다룬다.
- Playwright/MSW, dashboard equity chart, `/runs/[runId]` 탭 UX만 대상으로 삼는 것은 현재 backlog 정리에 맞다.
- “새 기능 추가가 아니라 Phase 7 완료 기준 충족”이라는 framing도 적절하다.

### 1.2 `/runs/[runId]` 탭화 계획은 현재 코드 구조와 잘 맞는다

근거:
- `frontend/app/runs/[runId]/page.tsx`
- `frontend/components/ui/tabs.tsx`
- `prd/phase_7_5_prd.md:92-101`
- `prd/phase_7_5_implementation_plan.md:55-67`, `245-278`

판단:
- 현재 `/runs/[runId]`에는 이미 다음 구성요소가 모두 들어 있다.
  - `RunSummaryGrid`
  - `EquityCurveChart`
  - `DrawdownChart`
  - `TradeScatterChart`
  - `SignalsTable`
  - `FillsTable`
  - `TradesTable`
- 즉 “새 데이터 로직”이 아니라 **기존 컴포넌트 재조합**에 가깝다.
- `frontend/components/ui/tabs.tsx`도 이미 존재하므로 탭 프리미티브를 새로 만들 필요가 없을 가능성이 높다.

이 부분은 Plan의 강한 지점이다.

### 1.3 Playwright를 `next build` + `next start` 기준으로 검증하려는 방향은 좋다

근거:
- `prd/phase_7_5_prd.md:47-52`, `68-84`
- `prd/phase_7_5_implementation_plan.md:30-45`, `97-123`

외부 기준:
- Next.js 공식 Playwright 가이드는 프로덕션에 가까운 서버 상태에서 검증하는 흐름이 자연스럽다.
- Playwright 공식 문서도 `webServer` + `baseURL` 기반 smoke/e2e 구성을 권장한다.

판단:
- `next dev` 기반 임시 검증보다 `next build` 결과를 `next start`로 띄우는 쪽이 더 현실적이다.
- 따라서 Epic A의 기본 방향은 합리적이다.

---

## 2. 수정이 필요한 점

### 2.1 `/runs` smoke test와 MSW handler 범위가 실제 페이지 동작과 맞지 않는다

근거:
- `prd/phase_7_5_prd.md:72-78`
- `prd/phase_7_5_implementation_plan.md:132-137`
- `frontend/app/runs/page.tsx:46-84`
- `frontend/store/runsStore.ts`
- `frontend/lib/api/backtests.ts`

문제:
- 계획 문서는 `/runs` 페이지를 위해 `GET /api/v1/backtests` 목록 endpoint를 mock하라고 적고 있다.
- 하지만 현재 `/runs` 페이지는 목록 endpoint를 쓰지 않는다.
- 실제로는 Zustand의 `runsStore`에 저장된 run id 목록을 읽고, 각 run id에 대해 개별 `getBacktestRun(runId)`를 refetch하는 구조다.

왜 문제인가:
- 지금 계획대로 handler를 만들어도 `/runs` smoke test가 기대대로 동작하지 않을 수 있다.
- 계획 문서 3종이 서로는 일관되지만, **현재 코드와는 일관되지 않는다.**

권장 수정:
- Epic A 문서에서 `/runs` smoke test 전략을 둘 중 하나로 명확히 고친다.
  1. 테스트 시작 전에 `runsStore` localStorage seed를 주입한다.
  2. `/runs` smoke test를 목록 페이지 대신 `run detail` 또는 다른 deterministic route로 바꾼다.

### 2.2 Tabs 컴포넌트는 “있는지 확인 후 추가”가 아니라 “이미 존재하므로 재사용”으로 문서를 줄여야 한다

근거:
- `frontend/components/ui/tabs.tsx`
- `prd/phase_7_5_prd.md:99`, `160`
- `prd/phase_7_5_implementation_plan.md:26`, `87`, `227-241`

문제:
- 현재 문서는 Tabs가 없을 수도 있다는 전제로 여러 단계를 적고 있다.
- 하지만 실제로는 이미 Base UI 기반 `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent` 래퍼가 존재한다.

권장 수정:
- Step 7.5-C1은 “존재 확인 및 인터페이스 적합성 검토” 수준으로 축소한다.
- 신규 추가 가능성은 fallback note 정도로만 남기는 편이 낫다.

### 2.3 Phase 7.5 task 문서의 broader/manual verification이 너무 느슨하다

근거:
- `prd/phase_7_5_task.md:174-184`

문제:
- 현재 manual verification은 탭 전환/차트 표시 정도만 다룬다.
- 하지만 Step A는 Service Worker 기반 mocking을 포함하므로, 실제로는 다음도 체크해야 한다.
  - SW 등록 race 없이 첫 API 호출부터 mock이 적용되는지
  - `ApiSettingsBar` persisted state가 test를 오염시키지 않는지
  - `/runs`가 local storage 상태 없이도 deterministic하게 동작하는지

권장 수정:
- manual verification에 테스트 state isolation 항목을 추가한다.

---

## 3. 바로 구현 시 위험한 가정

### 3.1 dashboard equity chart는 현재 API 타입만으로는 자연스럽게 구현되지 않는다

근거:
- `frontend/lib/api/types.ts:2-23`
- `frontend/lib/api/dashboard.ts:1-11`
- `frontend/hooks/useDashboardPolling.ts:7-46`
- `prd/phase_7_5_prd.md:53-58`, `85-90`
- `prd/phase_7_5_implementation_plan.md:46-54`, `170-205`

위험:
- 현재 타입에는 equity/time series/portfolio value/total value 같은 필드가 없다.
- `DashboardStatus`는 상태 정보 위주이고,
- `PositionsResponse`는 `positions[]`와 `cash`만 준다.
- 계획 문서는 `totalValue` 누적 또는 기존 응답 활용을 적고 있는데, **현 코드상 `totalValue`라는 필드는 존재하지 않는다.**

의미:
- 지금 문서대로 구현에 바로 들어가면, 차트는 결국 “임의로 계산한 근사치” 또는 “새로 정의한 비공식 파생치”가 될 가능성이 높다.
- 이건 PRD가 원하는 “portfolio equity chart 완성”으로 보기 애매할 수 있다.

권장:
- Step B1을 단순 “확인”이 아니라 **go/no-go gate**로 격상해야 한다.
- equity를 신뢰 가능하게 파생할 공식이 문서화되지 않으면,
  - B2/B3 구현은 보류하거나
  - 이 항목은 Phase 8로 넘기는 것이 더 정직하다.

### 3.2 MSW browser worker를 Playwright에서 쓰는 방식은 race condition을 부를 수 있다

근거:
- `prd/phase_7_5_prd.md:47-52`
- `prd/phase_7_5_implementation_plan.md:30-45`, `127-145`, `317-324`

외부 기준:
- MSW browser 모드는 worker file이 `public/`에서 서빙되어야 하고, `worker.start()`가 비동기라 초기 요청보다 늦게 붙으면 첫 fetch를 놓칠 수 있다.
- Playwright는 보통 `webServer` 기반으로 app을 띄우고 브라우저를 붙이므로, 초기 hydration/query fetch 타이밍과 SW registration 타이밍이 충돌할 수 있다.

의미:
- 지금 계획은 가능하지만, Step A를 너무 쉽게 보면 flaky smoke test가 나올 수 있다.

권장:
- 문서에 “SW registration race가 있으면 Node interception 또는 Playwright route mocking fallback”을 더 강하게 적어야 한다.
- 현재 Risk/Fallback 섹션에도 비슷한 문구가 있지만, **실행 순서의 결정 포인트**로는 부족하다.

### 3.3 `/runs/[runId]` 탭은 접근성 요구와 데이터 조건부 렌더링을 같이 고려해야 한다

근거:
- `frontend/app/runs/[runId]/page.tsx:40-45`, `90-105`
- `prd/phase_7_5_prd.md:94-101`
- `prd/phase_7_5_implementation_plan.md:245-278`

위험:
- 현재 analytics는 `isSucceeded`일 때만 fetch되고, `analyticsQuery.data`가 있을 때만 일부 UI가 렌더링된다.
- 계획 문서는 4개 탭 구성을 고정적으로 적고 있지만, analytics가 없는 실행에서 Summary/Charts/Trades 탭이 어떤 상태를 보여줄지 충분히 설명하지 않는다.

권장:
- `RunDetailTabs` 설계에 “analytics unavailable state”를 명시적으로 넣는다.
- 탭은 WAI-ARIA tabs pattern에 맞는 keyboard/focus 동작을 만족해야 한다는 점도 task/validation에 직접 적는 편이 좋다.

---

## 4. Recommended judgment

### 결론

이 계획은 **폐기할 필요는 없다.**

오히려:
- Epic C (`/runs/[runId]` 탭화)는 바로 구현해도 될 정도로 적합성이 높고,
- Epic A (Playwright + MSW)도 방향은 좋다.

하지만 다음 두 부분은 구현 전 수정이 필요하다.

1. `/runs` smoke test의 데이터 소스 전제 수정
2. dashboard equity chart 데이터 소스 전략을 더 엄격하게 정의

### 가장 정확한 평가 문장

> Phase 7.5 계획은 전체 방향과 범위 설정은 적절하지만,
> `/runs` 목록 smoke test와 dashboard equity chart의 데이터 전제는 현재 `frontend/` 구현과 완전히 맞지 않는다.
> 따라서 구현 전 문서 보정이 필요하며,
> 특히 Epic B는 data-source gate를 먼저 통과한 뒤 진행하는 것이 안전하다.

---

## 5. Suggested document changes before implementation

1. `phase_7_5_prd.md`, `phase_7_5_implementation_plan.md`, `phase_7_5_task.md`에서
   - `/runs` 목록 mock 전략을 현재 `runsStore` 기반 동작에 맞게 수정
2. `phase_7_5_implementation_plan.md`에서
   - Step 7.5-B1을 **go/no-go gate**로 격상
   - equity를 신뢰 가능하게 파생할 공식이 없으면 B2/B3를 보류하도록 명시
3. `phase_7_5_implementation_plan.md`와 `phase_7_5_task.md`에서
   - Tabs는 신규 추가보다 기존 `components/ui/tabs.tsx` 재사용 전제로 단순화
4. `phase_7_5_task.md` manual verification에
   - SW registration race
   - localStorage/API settings state isolation
   - analytics unavailable state
   를 추가
