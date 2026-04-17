# Phase 11 PRD

관련 문서:
- 이전 phase 범위/결과: `prd/phase_10_prd.md`
- 이전 phase 실행 검증: `prd/phase_10_task.md`
- 아키텍처 개요: `docs/architecture/overview.ko.md`
- 워크스페이스 분석: `docs/architecture/workspace-analysis.ko.md`
- 사용자 유즈케이스: `docs/architecture/user-use-cases.ko.md`
- 상세 구현 계획: `prd/phase_11_implementation_plan.md`
- 실행 추적: `prd/phase_11_task.md`

## 문서 목적

Phase 10으로 백테스트 실행 경로는 비동기 run lifecycle과 저장소 기반 조회 계약을 갖추게 되었다. 그러나 `docs/architecture/workspace-analysis.ko.md`가 지적한 또 다른 핵심 공백인 **live loop orchestration 부재**는 여전히 남아 있다. 현재 구현은 `LiveTradingLoop` 자체와 대시보드 모니터링 표면은 존재하지만, API 서버가 live loop를 시작/소유/중지하는 내장 흐름은 없다.

코드 기준으로도 이 공백은 명확하다. `app.services.run_live_paper()`와 `run_live_execution()`은 CLI에서 직접 호출될 때 현재 프로세스를 점유하는 blocking 경로이고, `api.server.create_app(live_loop=...)`는 외부에서 이미 생성된 loop를 단순 attach만 한다. 프론트엔드 대시보드는 `pause`, `resume`, `reset`만 보낼 수 있고, loop가 없는 상태에서 이를 생성하거나 종료하는 워크플로는 없다.

Phase 11은 이 간극을 메우기 위해 **API 프로세스가 단일 live runtime session을 소유하는 orchestration 계층**을 도입하고, 프론트엔드에서 preflight 이후 paper/live 실행을 시작하고 종료할 수 있는 1급 워크플로를 정의한다.

## Goal

1. API 서버가 단일 `LiveTradingLoop` 세션을 background thread로 시작, 소유, 종료할 수 있게 한다.
2. 운영자가 프론트엔드 또는 HTTP API를 통해 `paper` 또는 guarded `live` 실행을 시작하고, 현재 실행을 안전하게 중지할 수 있게 한다.
3. 대시보드가 외부에서 attach된 loop를 가정하지 않고, API가 소유한 runtime session의 상태를 직접 보여주도록 정렬한다.
4. 기존 `pause`, `resume`, `reset` 제어와 SSE/positions/equity/event 조회는 유지하면서, `start`와 `stop` lifecycle만 보강한다.

구현은 반드시 다음 원칙을 지켜야 한다.

- `LiveTradingLoop`와 `execute_trading_step()`의 기존 trading semantics는 유지한다.
- 한 API 프로세스 안에서 동시에 하나의 live session만 허용한다.
- `live_execution=live`는 기존 KIS guard와 `TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true`를 그대로 따라야 한다.
- `paper`와 `live` 모두 동일 orchestration 표면을 사용하되, start 직전 preflight를 반드시 거친다.
- CLI 경로는 유지한다. Phase 11은 API/프론트엔드 orchestration을 추가하는 것이지 CLI를 제거하는 phase가 아니다.

## Current Baseline

- `src/trading_system/app/services.py`의 `run_live_paper()`는 `LiveTradingLoop(...).run()`을 직접 호출하므로 blocking 경로다.
- `run_live_execution()` 역시 내부적으로 `run_live_paper()`를 호출하므로, API가 이를 직접 사용하면 요청-수명과 runtime-수명이 결합된다.
- `src/trading_system/api/server.py`는 `create_app(live_loop=...)` 인자로 외부 loop를 받아 `app.state.live_loop`에 attach할 뿐, loop를 생성하거나 중지하지 않는다.
- `src/trading_system/api/routes/dashboard.py`는 `pause`, `resume`, `reset`만 지원하고, loop가 없으면 `503 No live trading loop is running.` 을 반환한다.
- `frontend/components/dashboard/ControlButtons.tsx`는 `pause`, `resume`, `reset` 버튼만 제공한다.
- `frontend/app/dashboard/page.tsx`는 연결 여부를 표시하지만, disconnected 상태에서 operator가 바로 runtime을 시작할 수는 없다.
- `workspace-analysis.ko.md`는 App 레이어와 더 넓은 프로덕션 갭에서 모두 “live loop 프로세스를 시작하고 소유하는 내장 프론트엔드/API 워크플로가 아직 없다”고 적시한다.
- `user-use-cases.ko.md`의 UC-07, UC-09도 대시보드가 attached live loop가 있는 API 서버를 전제하고 있으며, API/UI에서 직접 `stop` 제어가 없다고 명시한다.
- `ControlActionDTO`는 `pause`, `resume`, `reset`만 허용하고 `stop`은 422가 난다.

## Non-Goals

- 다중 live session 동시 실행
- 분산 runtime supervisor 또는 별도 worker 프로세스 매니저 도입
- 전략/리스크 파라미터의 런타임 hot-reload
- live session의 자동 재시작 정책
- 브로커 reconnect orchestration 고도화
- 주문 lifecycle durable store 도입
- 대시보드에서 liquidation-all, parameter mutate, account switch 제공
- 백테스트/패턴/전략 UX 리디자인

## Hard Decisions

### D-1. API 프로세스는 단일 live runtime controller를 소유한다

- 현재 아키텍처는 `app.state.live_loop`를 기준으로 dashboard 표면이 연결되어 있으므로, 최소 변경으로는 API가 이 값을 직접 관리하는 controller를 추가하는 것이 가장 일관적이다.
- 다중 세션이나 외부 supervisor를 바로 도입하면 현재 scope를 크게 넘는다.
- `app.state.live_runtime_controller`가 thread, loop reference, last launch config, last error를 소유하고, `app.state.live_loop`는 active loop가 있을 때만 노출한다.

### D-2. Start는 별도 runtime route로 분리하고, 기존 dashboard control은 attached loop 제어에 집중시킨다

- `pause`, `resume`, `reset`은 이미 “실행 중 loop 제어” semantics를 가진다.
- `start`는 새 loop를 생성하는 orchestration이고 요구 payload도 크므로 같은 control enum에 넣기보다 별도 route로 분리하는 편이 계약이 명확하다.
- `stop`은 active loop lifecycle 종료이므로 기존 dashboard control에 추가하는 것이 자연스럽다.

### D-3. Start 요청은 preflight를 내장 호출한 뒤에만 session을 생성한다

- 운영자가 `preflight`와 `start`를 별도로 호출하는 UI는 유지할 수 있지만, 서버는 최종 `start` 직전에 동일 검증을 한번 더 수행해야 한다.
- 이를 통해 stale config, secret 변경, market closed 등의 상태를 final gate에서 다시 차단할 수 있다.

### D-4. Stop은 graceful stop을 우선하고 hard kill은 도입하지 않는다

- `LiveTradingLoop`는 이미 `STOPPED` 상태를 인식하므로, controller는 먼저 graceful stop signal을 보내고 join timeout을 기다리는 방식으로 충분하다.
- hard kill/thread terminate는 Python thread 모델상 안전하지 않으며 현재 scope에서 다룰 일이 아니다.

### D-5. 프론트엔드는 “대시보드 접속 전제”가 아니라 “대시보드에서 runtime 시작” 모델로 이동한다

- 현재 dashboard는 connected/disconnected indicator만 보여주며, disconnected 상태에서는 operator가 할 수 있는 일이 없다.
- runtime launch panel을 dashboard에 추가해 symbol/provider/broker/live_execution을 입력하고 시작하도록 만드는 것이 운영자 흐름에 가장 맞다.
- 단, advanced config 전부를 노출하기보다 현재 API DTO가 이미 다루는 최소 런타임 설정부터 시작한다.

## Product Requirements

### PR-1. Live runtime controller

- API 프로세스는 단일 active live session만 허용한다.
- controller는 active thread, active `LiveTradingLoop`, session metadata, last error를 추적한다.
- active session이 있을 때만 `app.state.live_loop`를 세팅하고, 종료되면 clear 한다.

### PR-2. Runtime start API

- 새 route는 live settings payload를 받아 `paper` 또는 `live` 실행을 시작한다.
- start 직전 서버가 동일 payload로 `preflight`를 다시 수행한다.
- active session이 이미 있으면 `409 Conflict`를 반환한다.
- 성공 시 session id, mode, execution type, symbols, started state를 반환한다.

### PR-3. Runtime stop API

- active loop가 있으면 graceful stop을 요청하고 thread join을 시도한다.
- stop 후 dashboard status는 disconnected 또는 stopped semantics를 반환해야 한다.
- active session이 없으면 명확한 no-op 또는 `409` 정책을 일관되게 반환해야 한다.

### PR-4. Dashboard/API status enrichment

- dashboard status는 active runtime이 없는 경우에도 operator가 이해할 수 있는 session/controller 상태를 반환해야 한다.
- `pause`, `resume`, `reset`, `stop`의 허용 상태 전이를 명시적으로 관리해야 한다.
- start/stop 이후 status, positions, events, equity 조회가 controller 상태와 일관되어야 한다.

### PR-5. Frontend launch flow

- dashboard에 runtime launch panel을 추가한다.
- operator는 symbols, provider, broker, `paper|live`를 입력하고 start를 요청할 수 있어야 한다.
- active session이 없을 때는 control buttons 대신 launch/disabled 상태가 보여야 한다.
- active session 중에는 duplicate start가 막혀야 한다.

### PR-6. Operator docs and examples

- README와 runbook은 “API 서버만 띄우는 것”이 아니라 “API가 live session을 시작/중지하는 방식”을 설명해야 한다.
- examples/configs는 live launch에 필요한 최소 payload 예시를 제공해야 한다.

## Scope By Epic

### Epic A. Runtime controller와 loop ownership

목표:
- API 프로세스가 live loop lifecycle을 직접 소유하도록 만든다.

포함:
- single-session controller
- background thread start/join
- `app.state.live_loop` attach/detach
- graceful stop

제외:
- multi-session orchestration
- process supervisor/daemon manager

### Epic B. Live runtime API contracts

목표:
- start/stop/status 제어를 API 계약으로 명확히 정의한다.

포함:
- start route
- stop control 추가
- 409/503/error semantics
- preflight-on-start gate

제외:
- arbitrary runtime parameter mutation
- scheduler/cron launch

### Epic C. Dashboard launch UX

목표:
- operator가 dashboard에서 직접 runtime을 시작하고 제어할 수 있게 한다.

포함:
- launch form
- active/inactive UI state 분기
- duplicate start guard
- stop button

제외:
- 대규모 대시보드 리디자인
- multi-account session chooser

## Impacted Files

### Runtime orchestration
- `src/trading_system/app/services.py`
- `src/trading_system/app/loop.py`
- `src/trading_system/app/live_runtime_controller.py`
- `src/trading_system/api/server.py`

### API routes and schemas
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/routes/dashboard.py`
- `src/trading_system/api/routes/live_runtime.py`
- `src/trading_system/api/schemas.py`

### Frontend dashboard flow
- `frontend/app/dashboard/page.tsx`
- `frontend/components/dashboard/ControlButtons.tsx`
- `frontend/components/dashboard/RuntimeLaunchForm.tsx`
- `frontend/lib/api/dashboard.ts`
- `frontend/lib/api/types.ts`
- `frontend/hooks/useDashboardPolling.ts`
- `frontend/hooks/useDashboardStream.ts`

### Validation and docs
- `tests/unit/test_dashboard_routes.py`
- `tests/unit/test_api_server.py`
- `tests/unit/test_live_runtime_controller.py`
- `tests/integration/test_live_runtime_api_integration.py`
- `README.md`
- `docs/runbooks/deploy-production.md`
- `docs/runbooks/deploy-production.ko.md`

## Delivery Slices

### Slice 0. Runtime controller 도입
- API가 단일 live loop를 thread 기반으로 소유하는 controller를 추가한다.

### Slice 1. Start/stop API 계약 정리
- live start route와 stop semantics를 추가해 controller를 API에서 제어한다.

### Slice 2. Dashboard launch UX 반영
- disconnected dashboard에서 runtime을 시작하고 active session을 제어할 수 있게 한다.

### Slice 3. 문서와 검증 보강
- 운영자 문서, 테스트, 수동 검증 체크리스트를 새 orchestration 모델에 맞게 정리한다.

## Success Metrics

- operator가 CLI 없이 API/프론트엔드만으로 live paper session을 시작하고 종료할 수 있다.
- active session이 없을 때 dashboard가 단순 503이 아니라 launch 가능한 상태를 보여준다.
- active session 중 duplicate start 요청은 명시적으로 거절된다.
- `pause`, `resume`, `reset`, `stop`이 session lifecycle과 모순 없이 동작한다.
- 서버 재시작 후 controller 상태가 clean하게 초기화되고, stale `app.state.live_loop` 참조가 남지 않는다.

## Risks and Follow-up

- background thread 기반 live orchestration은 단일 API 프로세스 전제다. 향후 multi-instance deployment에서는 leader ownership이 추가로 필요하다.
- live stop은 graceful semantics만 제공하므로, broker call이 장시간 block 되면 stop latency가 남을 수 있다.
- UI에서 모든 live settings를 바로 노출하면 operator 실수 가능성이 커진다. 초기 scope는 최소 필드에 제한하는 편이 안전하다.
- 후속 phase로는 stronger reconciliation authority, config parity, operational hardening을 각각 별도 phase로 분리하는 것이 적절하다.
