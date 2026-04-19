# Phase 12 Task Breakdown

## Usage

- 이 파일은 Phase 12 구현 진행 상황과 검증 증적을 기록한다.
- 체크박스는 실제 구현 작업과 검증 기준을 뜻한다.
- 각 slice가 끝날 때 `Execution Log`를 갱신한다.
- PRD 수준 범위는 `phase_12_prd.md`를 기준으로 한다.
- 상세 설계와 순서는 `phase_12_implementation_plan.md`를 기준으로 한다.

## Status Note

- 이 문서는 `prd/phase_12_prd.md`의 실행 추적 문서다.
- 이번 문서는 active backlog가 아니라, 이미 수행된 작업을 retrospective하게 Phase 12 산출물로 정리한 기록이다.
- 체크박스는 실제 구현 완료 여부와 확보된 검증 증적을 기준으로 표기한다.

## Phase 12-0. Structured preflight result 모델 확장

- [x] `src/trading_system/app/services.py`에 `ReadinessCheck`, `SymbolReadiness` 모델 추가
- [x] `PreflightCheckResult`에 `blocking_reasons`, `warnings`, `checks`, `symbol_checks`, `next_allowed_actions`, `checked_at` 추가
- [x] generic live path와 KIS preflight path가 모두 structured readiness를 생성하도록 정리
- [x] `src/trading_system/api/schemas.py`에 대응 DTO 필드 추가
- [x] `src/trading_system/api/routes/backtest.py`에 preflight 결과 변환 helper 추가
- [x] `src/trading_system/api/routes/live_runtime.py`가 start 응답에 preflight snapshot을 포함하도록 변경

Exit criteria:
- preflight endpoint와 runtime start endpoint가 operator-facing structured readiness contract를 반환한다.

## Phase 12-1. Controller와 dashboard status 문맥 확장

- [x] `src/trading_system/app/live_runtime_controller.py`가 last preflight snapshot을 저장하도록 확장
- [x] explicit preflight와 runtime start가 모두 controller에 preflight를 기록하도록 연결
- [x] `src/trading_system/api/routes/dashboard.py`에 `controller_state_detail`, `active`, `broker`, `stop_supported` 반영
- [x] dashboard status가 `last_preflight`, `latest_incident`를 반환하도록 확장
- [x] active loop가 없는 경우에도 status route가 `200`으로 controller/preflight 문맥을 반환하도록 유지

Exit criteria:
- dashboard status만 조회해도 operator가 현재 controller 상태와 마지막 launch 판단 근거를 이해할 수 있다.

## Phase 12-2. Launch form과 dashboard 운영 콘솔 구현

- [x] `frontend/lib/api/dashboard.ts`에 live preflight client 추가
- [x] `frontend/lib/api/types.ts`에 readiness/status 타입 추가
- [x] `frontend/components/dashboard/RuntimeLaunchForm.tsx`를 preflight-first launch form으로 재구성
- [x] launch payload signature 기반 freshness 판단을 추가해 stale preflight 상태에서 start를 막음
- [x] guarded live launch에 confirmation dialog 추가
- [x] `frontend/app/dashboard/page.tsx`에 runtime briefing / last preflight / latest incident / reconciliation card 추가
- [x] `frontend/components/dashboard/DashboardMetrics.tsx`가 provider/broker/live_execution 요약을 표시하도록 정리
- [x] `frontend/hooks/useDashboardPolling.ts`가 enriched status contract를 기준으로 active runtime을 판단하도록 조정

Exit criteria:
- operator가 dashboard에서 preflight를 먼저 읽고, 그 결과가 fresh한 경우에만 launch를 진행할 수 있다.

## Phase 12-3. 문서와 검증 기록 정리

- [x] `README.md`에 enriched preflight/start semantics 반영
- [x] `docs/runbooks/deploy-production.md`에 preflight-first launch 절차 반영
- [x] `docs/runbooks/deploy-production.ko.md`에 preflight-first launch 절차 반영
- [x] `ruff check`로 touched backend/test 파일 검증
- [x] `frontend` lint/build 검증 완료
- [x] `tests/unit/test_app_services.py`, `tests/integration/test_kis_preflight_integration.py`, `tests/unit/test_live_runtime_controller.py`, `tests/unit/test_live_runtime_routes.py` 실행 및 통과
- [ ] `TestClient(create_app())` 기반 route 회귀 검증 완료

Exit criteria:
- operator-facing docs와 phase 기록이 실제 코드/검증 상태와 일치한다.

## Verification Checklist

### Required unit tests

- [x] `UV_CACHE_DIR=.uv-cache uv run --python .venv/bin/python --no-sync pytest tests/unit/test_app_services.py tests/unit/test_live_runtime_controller.py tests/unit/test_live_runtime_routes.py -q`
- [x] `ruff check src/trading_system/app/services.py src/trading_system/app/live_runtime_controller.py src/trading_system/api/routes/backtest.py src/trading_system/api/routes/dashboard.py src/trading_system/api/routes/live_runtime.py src/trading_system/api/schemas.py tests/unit/test_live_runtime_routes.py tests/unit/test_dashboard_routes.py tests/unit/test_api_server.py tests/unit/test_api_backtest_schema.py tests/integration/test_live_runtime_api_integration.py`

### Required integration tests

- [x] `UV_CACHE_DIR=.uv-cache uv run --python .venv/bin/python --no-sync pytest tests/integration/test_kis_preflight_integration.py tests/integration/test_live_runtime_api_integration.py -q`

### Broader regression

- [x] `cd frontend && npm run lint`
- [x] `cd frontend && npm run build`
- [ ] `DATABASE_URL='' UV_CACHE_DIR=.uv-cache uv run --python .venv/bin/python --no-sync pytest tests/unit/test_dashboard_routes.py tests/unit/test_api_server.py tests/unit/test_api_backtest_schema.py tests/integration/test_live_runtime_api_integration.py`

### Manual verification

- [ ] dashboard에서 preflight 결과 패널을 실제 브라우저로 확인
- [ ] preflight 후 설정 변경 시 start 비활성화 동작 확인
- [ ] guarded live confirmation dialog 상호작용 확인
- [ ] status 화면에서 last preflight / latest incident 카드 확인

## Execution Log

### Date
- 2026-04-19

### Owner
- Codex

### Slice completed
- Phase 12-0: structured preflight result 모델 확장
- Phase 12-1: controller last preflight / dashboard status enrichment
- Phase 12-2: preflight-first launch form과 운영 콘솔 UI 구현
- Phase 12-3: README / deploy runbook / 테스트 기록 정리

### Scope implemented
- `PreflightCheckResult`를 structured readiness contract로 확장하고, KIS preflight 결과를 blocking reason / warning / check / symbol check 단위로 분류했다.
- `LiveRuntimeController`가 마지막 preflight snapshot을 기억하게 했고, explicit preflight와 runtime start 모두 이를 기록하도록 연결했다.
- dashboard status가 `controller_state_detail`, `active`, `broker`, `stop_supported`, `last_preflight`, `latest_incident`를 반환하도록 확장했다.
- dashboard launch form을 preflight-first 흐름으로 재구성해, fresh preflight가 없는 경우 start를 막고 guarded live는 confirmation dialog를 거치게 만들었다.
- dashboard 메인 화면에 runtime briefing, last preflight, latest incident, reconciliation 컨텍스트를 추가했다.
- 운영 문서에 preflight-first launch 절차를 반영했다.

### Files changed
- `src/trading_system/app/services.py`
- `src/trading_system/app/live_runtime_controller.py`
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/routes/live_runtime.py`
- `src/trading_system/api/routes/dashboard.py`
- `src/trading_system/api/schemas.py`
- `frontend/components/dashboard/RuntimeLaunchForm.tsx`
- `frontend/app/dashboard/page.tsx`
- `frontend/components/dashboard/DashboardMetrics.tsx`
- `frontend/hooks/useDashboardPolling.ts`
- `frontend/lib/api/dashboard.ts`
- `frontend/lib/api/types.ts`
- `README.md`
- `docs/runbooks/deploy-production.md`
- `docs/runbooks/deploy-production.ko.md`
- `tests/unit/test_live_runtime_routes.py`
- `tests/unit/test_dashboard_routes.py`
- `tests/unit/test_api_server.py`
- `tests/unit/test_api_backtest_schema.py`
- `tests/integration/test_live_runtime_api_integration.py`
- `prd/phase_12_prd.md`
- `prd/phase_12_implementation_plan.md`
- `prd/phase_12_task.md`

### Commands run
- `ruff check src/trading_system/app/services.py src/trading_system/app/live_runtime_controller.py src/trading_system/api/routes/backtest.py src/trading_system/api/routes/dashboard.py src/trading_system/api/routes/live_runtime.py src/trading_system/api/schemas.py tests/unit/test_live_runtime_routes.py tests/unit/test_dashboard_routes.py tests/unit/test_api_server.py tests/unit/test_api_backtest_schema.py tests/integration/test_live_runtime_api_integration.py` → passed
- `UV_CACHE_DIR=.uv-cache uv run --python .venv/bin/python --no-sync pytest tests/unit/test_app_services.py tests/integration/test_kis_preflight_integration.py tests/unit/test_live_runtime_controller.py tests/unit/test_live_runtime_routes.py` → `29 passed`
- `cd frontend && npm run lint` → passed
- `cd frontend && npm run build` → passed
- `DATABASE_URL='' UV_CACHE_DIR=.uv-cache uv run --python .venv/bin/python --no-sync pytest tests/unit/test_dashboard_routes.py tests/unit/test_api_server.py tests/unit/test_api_backtest_schema.py tests/integration/test_live_runtime_api_integration.py` → 환경에서 `TestClient(create_app())` startup 정체로 완료 결과 미회수

### Validation results
- touched backend/service/controller 범위의 lint는 통과했다.
- 서비스/KIS preflight/controller/runtime route 검증은 통과했다.
- frontend lint/build는 통과했다.
- 일부 `TestClient(create_app())` 기반 route 회귀는 현재 환경에서 정체되어, 전체 증적은 확보하지 못했다.

### Risks / follow-up
- `dashboard_routes` / `api_server` / `api_backtest_schema` 계열 `TestClient` 검증이 환경 의존적으로 멈추는 원인은 아직 분리되지 않았다.
- 이번 phase는 운영 콘솔과 readiness contract 강화에 집중했으므로, run/session metadata 영속화와 audit trail 강화는 다음 phase로 남는다.
- 실제 브라우저 수동 검증과 E2E는 아직 수행하지 않았다.
