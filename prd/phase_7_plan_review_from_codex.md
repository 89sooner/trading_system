# Phase 7 Plan Review From Codex

## Findings

### 1. High: Step 0가 현재 API 설정 셸 의존성을 범위에 포함하지 않아, 계획대로 구현하면 초기 앱 셸이 바로 깨질 수 있음

관련 문서:
- `prd/phase_7_prd.md:25-29`
- `prd/phase_7_prd.md:79-80`
- `prd/phase_7_prd.md:253-256`
- `prd/phase_7_implementation_plan.md:87-92`
- `prd/phase_7_implementation_plan.md:180-193`

현재 프론트엔드 근거:
- `frontend/src/api/client.ts:22-35`
- `frontend/src/store/apiStore.ts:4-47`
- `frontend/src/components/shared/ApiSettingsBar.tsx:7-55`
- `frontend/src/routes/__root.tsx:6-20`

문제:
- 계획은 `frontend/src/api/`만 `lib/api/`로 이식한다고 적고 있지만, 현재 API 호출은 단순 환경변수 기반이 아니라 `useApiStore`의 `baseUrl`/`apiKey`에 직접 의존한다.
- 현재 운영자 워크플로는 루트 셸의 `ApiSettingsBar`에서 base URL과 API key를 바꾸는 방식인데, impacted files와 Step 0 파일 목록에는 `store/apiStore.ts`와 `components/shared/ApiSettingsBar.tsx`가 빠져 있다.
- 이 둘을 명시적으로 이식하지 않으면 Next.js 전환 직후 루트 레이아웃에서 현재 운영자 설정 UX가 사라지거나, `requestJson()`이 기대하는 store가 없어 모든 API 호출이 깨질 수 있다.

권장 수정:
- Step 0와 Impacted Files에 `frontend-next/store/apiStore.ts`와 `frontend-next/components/shared/ApiSettingsBar.tsx`를 명시적으로 추가한다.
- `NEXT_PUBLIC_API_BASE_URL`은 기본값만 제공하고, 현재처럼 operator override UI를 유지할지 제거할지 결정사항으로 고정한다.

### 2. High: “서버 컴포넌트 기본” 원칙과 “TanStack Query 클라이언트 유지” 전략이 충돌하며, `loading.tsx`/`error.tsx` 요구사항이 실제 상태 커버리지를 보장하지 않음

관련 문서:
- `prd/phase_7_prd.md:16-17`
- `prd/phase_7_prd.md:26-30`
- `prd/phase_7_prd.md:58-62`
- `prd/phase_7_prd.md:91-95`
- `prd/phase_7_implementation_plan.md:9-13`
- `prd/phase_7_implementation_plan.md:143-146`

문제:
- 계획은 App Router의 서버 컴포넌트를 기본 원칙으로 내세우면서도, 실제 데이터 페칭은 기존 TanStack Query 클라이언트 패턴을 유지한다고 못 박고 있다.
- 현재 화면 대부분은 대시보드 폴링, 전략/패턴 폼, 차트, API settings bar처럼 클라이언트 인터랙션 중심이다. 이 구조에서는 페이지 루트 상당수가 결국 `use client` 경계로 올라갈 가능성이 높다.
- 그런 상태에서 각 라우트에 `loading.tsx`와 `error.tsx`를 둔다는 요구는 App Router의 route-level loading/error와 TanStack Query 내부 loading/error를 혼동하게 만든다. 문서상으로는 상태 커버리지가 완전해 보이지만, 실제 구현에서는 route loading과 query loading이 별개라 요구사항이 중복되거나 공허해질 수 있다.

권장 수정:
- 서버 컴포넌트 사용 범위를 “레이아웃/정적 페이지 쉘/비인터랙티브 래퍼” 정도로 축소 명시한다.
- 상태 커버리지 요구사항을 `loading.tsx`/`error.tsx` 중심이 아니라 “route-level fallback + query-level fallback”의 이중 기준으로 다시 적는다.

### 3. Medium: Playwright smoke test 요구가 있지만, 테스트 하네스와 백엔드 준비 방식이 계획에 충분히 고정되지 않음

관련 문서:
- `prd/phase_7_prd.md:146-151`
- `prd/phase_7_prd.md:229-233`
- `prd/phase_7_prd.md:318`
- `prd/phase_7_implementation_plan.md:152-163`
- `prd/phase_7_implementation_plan.md:300-314`

현재 프론트엔드 근거:
- `frontend/package.json:6-10`
- 현재 저장소에 Playwright 관련 설정/의존성 부재

문제:
- 계획은 Playwright smoke test 3개를 요구하지만, 어떤 백엔드를 띄운 상태에서 검증할지, mock을 쓸지, 실 API를 붙일지, CI/로컬에서 어떤 명령으로 재현할지 고정하지 않았다.
- 특히 `/dashboard`와 `/runs`는 데이터 의존이 강해, 백엔드 없는 상태에서는 smoke의 의미가 크게 달라진다.
- 지금 문서만으로 구현을 시작하면 Step 4에서 “테스트를 작성했지만 신뢰도 낮음” 또는 “환경 구성이 없어 실행 불가”로 막힐 가능성이 크다.

권장 수정:
- Step 4에 “Playwright는 mock API를 사용할지, 로컬 FastAPI를 띄울지”를 먼저 결정하는 선행 항목을 추가한다.
- 검증 명령을 `frontend-next/package.json` 스크립트 수준으로 미리 정의하는 것이 좋다.

### 4. Medium: 클린 재구축 + 최종 교체 전략은 가능하지만, 현재 `frontend/`의 운영 자산 목록이 Step 5에서 충분히 체크되지 않음

관련 문서:
- `prd/phase_7_prd.md:76-80`
- `prd/phase_7_prd.md:296-300`
- `prd/phase_7_implementation_plan.md:317-337`

현재 프론트엔드 근거:
- `frontend/components.json`
- `frontend/package-lock.json`
- `frontend/src/lib/formatters.ts`
- `frontend/src/lib/patternParser.ts`
- `frontend/src/lib/strategyParser.ts`
- `frontend/src/store/apiStore.ts`

문제:
- Step 5는 `frontend-next/`를 `frontend/`로 교체한다고만 적고 있지만, 실제 교체 시점에는 shadcn 설정 파일, npm lockfile, parser 유틸, zustand store, 환경변수 문서, path alias 같은 자산도 함께 정리되어야 한다.
- 현재 문서상으로는 “API 클라이언트/타입/유틸리티 최대한 재활용” 정도만 적혀 있어, 마지막 교체 시 자산 누락 위험이 남는다.

권장 수정:
- Step 5 종료 조건에 “components.json, lockfile, env example, shared utils/store parity 확인”을 추가한다.

## Overall Assessment

계획의 큰 방향은 적절하다.

- Phase 6 이후 다음 단계로 프론트엔드 아키텍처 현대화와 UI 고도화를 잡은 점은 자연스럽다.
- 백엔드 API를 바꾸지 않고 프론트엔드만 교체한다는 원칙도 현재 저장소 구조와 맞다.
- 현재 라우트/페이지 구조를 기준으로 epic과 slice를 나눈 방식도 이해하기 쉽다.

다만 현 상태의 문서는 “바로 구현 시작 가능한 수준”까지는 아직 아니다.

- 가장 큰 이유는 현재 운영자용 프론트엔드 셸의 핵심 요소인 `ApiSettingsBar` + `apiStore`가 계획 문서에서 사실상 빠져 있기 때문이다.
- 그다음으로는 서버 컴포넌트 원칙과 클라이언트 Query 유지 전략이 충돌하고, Playwright 검증 전제가 충분히 고정되지 않은 점이 있다.

## Recommendation

추천 판단은 다음과 같다.

1. 이 계획을 폐기할 필요는 없다.
2. 다만 구현 전, 위 4개 이슈를 반영해 `phase_7_prd.md`와 `phase_7_implementation_plan.md`를 한 번 더 보정하는 것이 안전하다.
3. 특히 Step 0 파일 범위와 Step 4 검증 하네스 정의는 구현 착수 전에 먼저 수정하는 편이 좋다.
