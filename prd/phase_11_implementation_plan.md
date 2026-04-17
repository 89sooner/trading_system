# Phase 11 Implementation Plan

## Goal

Phase 11의 구현 목표는 API 프로세스가 단일 `LiveTradingLoop` 세션을 직접 소유하도록 만들고, 프론트엔드 대시보드에서 live paper/live execution을 시작하고 종료할 수 있는 운영자 워크플로를 제공하는 것이다.

핵심 구현 원칙:

1. `LiveTradingLoop`와 기존 trading-step semantics는 유지한다.
2. controller는 single-session ownership만 다룬다.
3. start 직전 preflight를 반드시 다시 수행한다.
4. dashboard control은 “active loop 제어”, runtime start는 “새 loop 생성”으로 분리한다.
5. CLI 경로와 attached-loop 하위 호환은 유지한다.

## Preconditions

- Phase 10의 async backtest 변경은 현재 baseline으로 간주한다.
- `app.state.live_loop`를 참조하는 dashboard routes가 이미 존재하므로, 새 controller는 이 값을 active loop에 맞춰 일관되게 관리해야 한다.
- 기존 `run_live_paper()`와 `run_live_execution()`은 blocking 호출이므로 controller 재사용 전에 loop 생성/실행 경계를 분리해야 한다.
- HTTP/ASGI 테스트 harness가 불안정할 수 있으므로 unit-first 전략으로 controller와 route semantics를 검증해야 한다.

## Locked Design Decisions

### 1. `LiveRuntimeController`를 새로 만들고 `app.state`에서 소유한다

- `src/trading_system/app/live_runtime_controller.py`에 single active session controller를 추가한다.
- controller는 thread, active loop reference, active session metadata, last error를 관리한다.
- server lifespan startup에서 controller를 생성하고, shutdown에서 active session이 있으면 graceful stop을 호출한다.

### 2. Start route는 별도 `live_runtime` 라우터로 분리한다

- `dashboard/control`은 active loop에 대한 `pause/resume/reset/stop`만 다루고, 새 session 시작은 별도 route가 담당한다.
- 시작 payload는 기존 `LivePreflightRequestDTO`와 최대한 같은 설정 shape를 재사용한다.

### 3. `AppServices`는 “loop를 직접 run”하는 메서드와 “loop를 생성”하는 메서드를 분리한다

- controller가 thread 안에서 `loop.run()`을 호출해야 하므로, `build_live_loop(...)` 또는 동등한 helper를 추가해 loop 생성과 실행을 분리한다.
- 기존 CLI 경로는 이 helper를 재사용하되, 사용자-facing 동작은 바꾸지 않는다.

### 4. Stop은 graceful stop + bounded join으로 구현한다

- controller는 active loop state를 `STOPPED`로 전환하고 join timeout을 기다린다.
- timeout을 넘기면 error 상태를 남기고 detached cleanup만 수행한다. hard thread kill은 하지 않는다.

### 5. Dashboard는 disconnected 상태에서 launch panel을 기본으로 보여준다

- connected 상태면 기존 metrics/control 중심 UI를 유지한다.
- disconnected 상태면 runtime start form과 현재 controller status/last error를 보여준다.
- operator가 start 성공 직후 바로 SSE/polling 흐름에 진입하도록 query invalidation을 포함한다.

## Contract Deltas

## A. Live runtime controller contract

대상:
- `src/trading_system/app/live_runtime_controller.py`
- `src/trading_system/app/services.py`
- `src/trading_system/app/loop.py`

필수 변화:
- controller가 active session 유무를 판별하고 start/stop을 제공해야 한다.
- `AppServices`가 blocking run 메서드와 reusable loop 생성 경계를 분리해야 한다.
- active loop attach/detach가 `app.state.live_loop`와 동기화돼야 한다.

비고:
- controller는 single-session만 허용한다.

## B. Live runtime API contract

대상:
- `src/trading_system/api/routes/live_runtime.py`
- `src/trading_system/api/routes/dashboard.py`
- `src/trading_system/api/schemas.py`
- `src/trading_system/api/server.py`

필수 변화:
- start route가 live payload를 받아 preflight 후 session을 생성해야 한다.
- stop control이 active loop 종료를 지원해야 한다.
- status DTO가 active/inactive runtime semantics를 더 명확히 노출해야 한다.
- server lifespan이 controller 생성과 shutdown cleanup을 책임져야 한다.

비고:
- attached-loop 하위 호환이 필요하므로 controller가 없거나 외부 loop가 attach된 경우도 고려한다.

## C. Frontend dashboard contract

대상:
- `frontend/app/dashboard/page.tsx`
- `frontend/components/dashboard/ControlButtons.tsx`
- `frontend/components/dashboard/RuntimeLaunchForm.tsx`
- `frontend/lib/api/dashboard.ts`
- `frontend/lib/api/types.ts`

필수 변화:
- disconnected 상태에서 launch form을 렌더링해야 한다.
- connected 상태에서 `stop`까지 포함한 control set을 보여줘야 한다.
- start/stop 후 dashboard queries와 stream fallback이 일관되게 갱신돼야 한다.

비고:
- 기존 metrics/event/equity panels는 유지한다.

## Sequenced Implementation

### Step 0. Controller와 loop 생성 경계 분리

목적:
- blocking CLI 경로와 API-owned runtime 경로를 동시에 만족하는 공통 기반을 만든다.

파일:
- `src/trading_system/app/services.py`
- `src/trading_system/app/loop.py`
- `src/trading_system/app/live_runtime_controller.py`
- `tests/unit/test_app_services.py`
- `tests/unit/test_live_runtime_controller.py`

구체 작업:
- `AppServices`에 live loop 생성 helper를 추가하고, 기존 `run_live_paper()`/`run_live_execution()`은 이를 재사용하게 정리한다.
- controller가 thread start, active session metadata, graceful stop을 관리하도록 구현한다.
- controller 단위 테스트에 duplicate start, stop without session, graceful stop, last error 기록 케이스를 추가한다.

종료 조건:
- controller가 thread 기반으로 loop를 시작/종료하고 active session 상태를 일관되게 유지한다.

### Step 1. Start/stop API와 schema 추가

목적:
- live runtime lifecycle을 HTTP 계약으로 노출한다.

파일:
- `src/trading_system/api/routes/live_runtime.py`
- `src/trading_system/api/routes/dashboard.py`
- `src/trading_system/api/schemas.py`
- `src/trading_system/api/server.py`
- `tests/unit/test_dashboard_routes.py`
- `tests/unit/test_api_server.py`
- `tests/integration/test_live_runtime_api_integration.py`

구체 작업:
- start payload/response DTO를 추가한다.
- `POST /api/v1/live/runtime/start`와 `POST /api/v1/live/runtime/stop` 또는 동등한 route를 구현한다.
- `dashboard/control`에 `stop`을 추가하고, 허용 상태 전이를 정리한다.
- start route가 내부적으로 preflight를 재실행하고 `409`/`503` semantics를 명확히 반환하도록 만든다.

종료 조건:
- operator가 API만으로 live paper session을 시작/중지할 수 있고 duplicate start가 거절된다.

### Step 2. Dashboard launch UX 구현

목적:
- API contract를 operator가 직접 사용할 수 있는 UI로 연결한다.

파일:
- `frontend/app/dashboard/page.tsx`
- `frontend/components/dashboard/ControlButtons.tsx`
- `frontend/components/dashboard/RuntimeLaunchForm.tsx`
- `frontend/lib/api/dashboard.ts`
- `frontend/lib/api/types.ts`
- `frontend/hooks/useDashboardPolling.ts`
- `frontend/hooks/useDashboardStream.ts`

구체 작업:
- disconnected 상태에서 launch form을 렌더링한다.
- connected 상태에서 `stop` 버튼을 포함한 control set을 제공한다.
- start success 후 dashboard query invalidate와 stream 연결 흐름을 정리한다.
- duplicate start와 validation error를 operator-friendly message로 보여준다.

종료 조건:
- dashboard에서 session start/stop이 가능하고, active/inactive UI 상태가 자연스럽게 전환된다.

### Step 3. Docs와 회귀 검증

목적:
- 새 orchestration 모델을 문서와 테스트에 반영한다.

파일:
- `README.md`
- `docs/runbooks/deploy-production.md`
- `docs/runbooks/deploy-production.ko.md`
- `tests/unit/test_live_runtime_controller.py`
- `tests/integration/test_live_runtime_api_integration.py`

구체 작업:
- 운영자 문서에 API-owned live session launch/stop 절차를 추가한다.
- 배포 후 점검 체크리스트에 runtime start/stop, dashboard attach 확인을 넣는다.
- touched tests 통과 후 broader regression을 실행한다.

종료 조건:
- 문서가 새 runtime ownership 모델을 설명하고, 핵심 unit/integration 검증이 확보된다.

## Validation Matrix

### Required unit tests
- `pytest tests/unit/test_live_runtime_controller.py -q`
- `pytest tests/unit/test_dashboard_routes.py -q`
- `pytest tests/unit/test_app_services.py -q`
- `pytest tests/unit/test_api_server.py -q -k live_runtime`

### Required integration tests
- `pytest tests/integration/test_live_runtime_api_integration.py -q`
- `pytest tests/integration/test_kis_preflight_integration.py -q`

### Manual verification
- dashboard disconnected 상태에서 runtime launch form이 보이는지 확인
- paper start 후 status/positions/events/equity가 연결되는지 확인
- stop 후 dashboard가 clean disconnected 상태로 돌아가는지 확인
- guarded live start가 market/secret/flag 조건을 다시 검증하는지 확인

## Recommended PR Slices

1. Controller + loop 생성 helper 분리
2. Start/stop API + schema + unit tests
3. Dashboard launch form + control UX
4. Docs + integration validation

## Risks and Fallbacks

- thread 기반 live runtime은 join timeout 시 stop latency가 남을 수 있다.

대응:
- Step 0에서 bounded join과 last-error 기록을 넣고, Step 3 수동 검증에서 stop latency를 명시적으로 확인한다.

- start route와 기존 preflight가 서로 다른 검증 결과를 낼 수 있다.

대응:
- Step 1에서 start가 내부적으로 동일 preflight 함수를 재사용하도록 강제한다.

- dashboard disconnected/connected 상태 전환이 꼬이면 operator UX가 혼란스러울 수 있다.

대응:
- Step 2에서 controller status를 explicit DTO로 노출하고 query invalidation을 start/stop 직후 수행한다.
