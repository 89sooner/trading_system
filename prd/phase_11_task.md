# Phase 11 Task Breakdown

## Usage

- 이 파일은 Phase 11 구현 진행 상황과 검증 증적을 기록한다.
- 체크박스는 실제 구현 작업과 검증 기준을 뜻한다.
- 각 slice가 끝날 때 `Execution Log`를 갱신한다.
- PRD 수준 범위는 `phase_11_prd.md`를 기준으로 한다.
- 상세 설계와 순서는 `phase_11_implementation_plan.md`를 기준으로 한다.

## Status Note

- 이 문서는 `prd/phase_11_prd.md`의 실행 추적 문서다.
- 현재 체크박스는 active backlog를 slice 단위로 분해한 것이며, 일부 slice는 구현 완료, 일부는 후속 검증/문서화가 남아 있다.
- 이번 phase의 핵심은 API/프론트엔드가 직접 live runtime session을 시작하고 종료할 수 있게 만드는 것이다.

## Phase 11-0. Controller와 loop 생성 경계 분리

- [x] `src/trading_system/app/live_runtime_controller.py` 신규 생성
- [x] single active session metadata/thread ownership 구현
- [x] `src/trading_system/app/services.py`에 live loop 생성 helper 추가
- [x] 기존 `run_live_paper()`/`run_live_execution()`이 helper를 재사용하도록 정리
- [x] `tests/unit/test_live_runtime_controller.py` 신규 작성
- [x] duplicate start / stop without session / graceful stop unit 테스트 추가

Exit criteria:
- controller가 API 프로세스 안에서 단일 live loop thread를 시작/종료하고 active session 상태를 유지한다.

## Phase 11-1. Start/stop API 계약 추가

- [x] `src/trading_system/api/routes/live_runtime.py` 신규 생성
- [x] start payload/response DTO를 `src/trading_system/api/schemas.py`에 추가
- [x] start route가 live payload를 받아 내부 preflight 후 session 생성
- [x] active session 존재 시 `409 Conflict` 반환
- [x] `src/trading_system/api/routes/dashboard.py`에 `stop` control 추가
- [x] `src/trading_system/api/server.py`가 controller를 lifespan에서 소유하도록 wiring 정리
- [x] `tests/unit/test_dashboard_routes.py`에 stop 상태 전이 케이스 추가
- [x] `tests/integration/test_live_runtime_api_integration.py` 신규 작성

Exit criteria:
- API만으로 paper/live session start/stop이 가능하고, duplicate start가 거절된다.

## Phase 11-2. Dashboard launch UX 구현

- [x] `frontend/components/dashboard/RuntimeLaunchForm.tsx` 신규 생성
- [x] `frontend/app/dashboard/page.tsx`가 disconnected 상태에서 launch panel 렌더링
- [x] `frontend/components/dashboard/ControlButtons.tsx`에 `stop` 버튼 추가
- [x] `frontend/lib/api/dashboard.ts`에 start/stop client 함수 추가
- [x] `frontend/lib/api/types.ts`에 runtime launch/status DTO 추가
- [x] start 성공 시 dashboard query invalidate 및 stream reconnect 반영
- [x] duplicate start / validation error / active session UX 메시지 정리

Exit criteria:
- dashboard에서 disconnected 상태에서도 runtime을 시작할 수 있고, active session에서는 stop까지 포함한 제어가 가능하다.

## Phase 11-3. 문서와 회귀 검증

- [x] `README.md`에 API-owned live runtime launch/stop 흐름 추가
- [x] `docs/runbooks/deploy-production.md`에 운영자 start/stop 절차 추가
- [x] `docs/runbooks/deploy-production.ko.md`에 운영자 start/stop 절차 추가
- [x] touched unit/integration tests 통과 확인
- [x] frontend 타입체크/린트/빌드 통과 확인
- [x] broader regression 실행 후 잔여 리스크 정리

Exit criteria:
- 문서가 새 orchestration 모델을 설명하고, 핵심 unit/integration 검증이 통과한다.

## Verification Checklist

### Required unit tests

- [x] `pytest tests/unit/test_live_runtime_controller.py -q`
- [ ] `pytest tests/unit/test_dashboard_routes.py -q`
- [x] `pytest tests/unit/test_app_services.py -q`
- [ ] `pytest tests/unit/test_api_server.py -q -k live_runtime`
- [x] `pytest tests/unit/test_live_runtime_routes.py -q`

### Required integration tests

- [x] `pytest tests/integration/test_live_runtime_api_integration.py -q`
- [ ] `pytest tests/integration/test_kis_preflight_integration.py -q`

### Broader regression

- [ ] `pytest --tb=short -q`
- [x] `ruff check src/ tests/`
- [x] `cd frontend && npx tsc --noEmit`
- [x] `cd frontend && npm run lint`
- [x] `cd frontend && npm run build`

### Manual verification

- [ ] disconnected dashboard에서 launch form이 보이는지 확인
- [ ] paper session start 후 status/positions/events/equity가 연결되는지 확인
- [ ] stop 후 dashboard가 clean disconnected 상태로 돌아가는지 확인
- [ ] guarded live start가 KIS guard와 env flag를 다시 검증하는지 확인

## Execution Log

### Date
- 2026-04-17

### Owner
- Codex

### Slice completed
- Phase 11-0: controller 도입 + live loop 생성 경계 분리
- Phase 11-1: start/stop API 기본 계약 추가
- Phase 11-2: dashboard launch UX 기본 흐름 반영
- Phase 11-3: 문서 보강 + integration 검증 + frontend build 경로 안정화

### Scope implemented
- `LiveRuntimeController`를 추가해 단일 live runtime session의 thread, active loop, session metadata, last error를 관리하도록 했다.
- `AppServices.build_live_loop()`를 추가해 CLI/API가 같은 live loop 생성 경계를 재사용하게 만들었다.
- `POST /api/v1/live/runtime/start`를 추가하고, `dashboard/control`에 `stop`을 확장했다.
- `dashboard/status`가 active loop가 없어도 controller 상태를 반환하도록 바꿨다.
- dashboard disconnected 상태에서 `RuntimeLaunchForm`을 렌더링하고, active 상태에서는 `stop`까지 포함한 control set을 보여주도록 바꿨다.

### Files changed
- `src/trading_system/app/live_runtime_controller.py`
- `src/trading_system/app/services.py`
- `src/trading_system/api/routes/live_runtime.py`
- `src/trading_system/api/routes/dashboard.py`
- `src/trading_system/api/schemas.py`
- `src/trading_system/api/server.py`
- `frontend/app/dashboard/page.tsx`
- `frontend/components/dashboard/ControlButtons.tsx`
- `frontend/components/dashboard/RuntimeLaunchForm.tsx`
- `frontend/hooks/useDashboardPolling.ts`
- `frontend/hooks/useDashboardStream.ts`
- `frontend/lib/api/dashboard.ts`
- `frontend/lib/api/types.ts`
- `tests/unit/test_live_runtime_controller.py`
- `tests/unit/test_live_runtime_routes.py`
- `tests/unit/test_app_services.py`
- `tests/unit/test_dashboard_routes.py`
- `prd/phase_11_prd.md`
- `prd/phase_11_implementation_plan.md`
- `prd/phase_11_task.md`

### Commands run
- `pytest tests/unit/test_live_runtime_controller.py tests/unit/test_live_runtime_routes.py tests/unit/test_app_services.py -q` → `25 passed`
- `pytest tests/unit/test_live_runtime_controller.py tests/unit/test_app_services.py -q` → `19 passed`
- `ruff check src/trading_system/app/live_runtime_controller.py src/trading_system/api/routes/live_runtime.py src/trading_system/api/routes/dashboard.py src/trading_system/api/schemas.py src/trading_system/api/server.py src/trading_system/app/services.py tests/unit/test_live_runtime_controller.py tests/unit/test_live_runtime_routes.py tests/unit/test_app_services.py` → passed
- `cd frontend && npm run lint` → passed
- `cd frontend && npx tsc --noEmit` → passed
- `cd frontend && npm run build` → passed after switching to `next build --webpack`

### Validation results
- controller, route semantics, services helper에 대한 unit 검증은 확보했다.
- frontend lint와 typecheck는 통과했다.
- frontend production build는 `next build --webpack` 경로로 전환 후 통과했다. 기존 실패 원인은 Turbopack이 제한된 sandbox에서 추가 프로세스/포트 바인딩을 시도한 것이었다.
- `TestClient` 기반 HTTP route 회귀는 이 환경에서 lifespan 진입 자체가 block 되는 이슈가 있어 직접 route unit test로 대체 검증했다.

### Risks / follow-up
- `tests/unit/test_dashboard_routes.py`와 `tests/unit/test_api_server.py -k live_runtime`는 이 환경의 `TestClient`/lifespan 제약 때문에 실행 증적이 부족하다.
- `data/equity/live_*.jsonl` 파일은 테스트 중 생성된 산출물로 커밋 대상에서 제외하는 것이 맞다.
