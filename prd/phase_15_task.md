# Phase 15 Task Breakdown

## Usage

- 이 파일은 Phase 15 구현 진행 상황과 검증 증적을 기록한다.
- 체크박스는 실제 구현 작업과 검증 기준을 뜻한다.
- 각 slice가 끝날 때 `Execution Log`를 갱신한다.
- PRD 수준 범위는 `phase_15_prd.md`를 기준으로 한다.
- 상세 설계와 순서는 `phase_15_implementation_plan.md`를 기준으로 한다.

## Status Note

- 이 문서는 `prd/phase_15_prd.md`의 실행 추적 문서다.
- 현재 체크박스는 active backlog를 slice 단위로 분해한 것이며, 아직 구현 완료를 의미하지 않는다.
- 이번 phase의 핵심은 broker open-order authority, live order audit 검증, audit search/export, strategy config parity다.

## Phase 15-0. Open-order contract and KIS parser

- [x] `src/trading_system/execution/broker.py`에 `OpenOrder`와 `OpenOrderSnapshot` DTO 추가
- [x] broker protocol에 optional `get_open_orders()` capability 추가
- [x] `ResilientBroker.get_open_orders()` resilience wrapper 추가
- [x] `src/trading_system/integrations/kis.py`에 KIS open/unresolved order 조회 메서드 추가
- [x] KIS open-order 응답 parser에서 필수 필드 누락을 fail-closed 오류로 처리
- [x] `src/trading_system/execution/kis_adapter.py`가 open-order snapshot을 반환하도록 연결
- [x] `tests/unit/test_kis_integration.py`에 정상/빈/누락/error 응답 케이스 추가

Exit criteria:
- KIS open-order parser와 adapter capability가 fixture 기반 unit test를 통과한다.

## Phase 15-1. Reconciliation pending authority hardening

- [x] live loop reconciliation 전에 open-order snapshot을 우선 조회
- [x] open-order snapshot이 있으면 pending symbols를 open-order source 기준으로 계산
- [x] open-order unsupported 상태에서는 기존 balance snapshot `pending_symbols` fallback 유지
- [x] open-order 조회 실패 시 portfolio book mutation 없이 reconciliation skip event 기록
- [x] logger payload에 `pending_source`와 pending symbol 수 포함
- [x] `tests/unit/test_reconciliation.py`에 pending source priority regression 추가
- [x] `tests/integration/test_kis_reconciliation_integration.py`에 open-order fail-closed 케이스 추가

Exit criteria:
- open-order source가 있는 경우 해당 source가 pending 판단의 우선 근거가 되고, 조회 실패 시 cash/position이 변경되지 않는다.

## Phase 15-2. Broker order id audit propagation and live audit verification

- [x] `FillEvent`에 optional `broker_order_id` 추가
- [x] KIS `_to_fill_event()`가 `KisOrderResult.order_id`를 `broker_order_id`로 전달
- [x] `execute_trading_step` fill event payload에 `broker_order_id` 포함
- [x] `OrderAuditRecord` 변환이 broker order id를 보존하는지 테스트 추가
- [x] direct live loop/service-boundary 테스트로 `scope=live_session`, `owner_id=session_id` audit record 생성 검증
- [x] audit append 실패가 live loop tick과 portfolio persistence를 깨지 않는 regression test 추가
- [x] `tests/integration/test_order_audit_integration.py`가 TestClient lifespan 없이 live owner audit을 검증하도록 정리

Exit criteria:
- KIS order id가 audit record의 `broker_order_id`에 보존되고, live session owner 기준 audit 생성 테스트가 통과한다.

## Phase 15-3. Order audit filter/export

- [x] `OrderAuditRepository.list()`에 `start`, `end`, `status`, `side`, `broker_order_id`, `sort` 필터 추가
- [x] file repository index/read path가 새 필터를 적용하도록 구현
- [x] Supabase repository SQL where/order 조건 확장
- [x] order audit list API query validation 추가
- [x] `/api/v1/order-audit/export` CSV/JSONL bounded response 추가
- [x] export 응답에 applied filter와 record count를 확인할 수 있는 header 또는 metadata 제공
- [x] frontend API client에 audit export 함수 추가
- [x] run detail 또는 session detail에 owner 기준 export action 추가
- [x] repository/route/export 테스트 추가

Exit criteria:
- API가 owner/time/status/broker id 기준 audit record를 필터링하고 CSV/JSONL export로 반환한다.

## Phase 15-4. Strategy config parity

- [x] `src/trading_system/config/settings.py`에 YAML `strategy` section typed parser 추가
- [x] YAML config를 `AppSettings`로 변환하는 helper 추가
- [x] CLI parser에 `--config`와 `--strategy-profile-id` 추가
- [x] CLI/config/API strategy validation semantics를 `AppSettings.validate()` 기준으로 정렬
- [x] `configs/base.yaml`에 strategy 설정 예시 추가
- [x] `examples/sample_backtest.yaml`, `sample_backtest_krx.yaml`, `sample_live_kis.yaml` 업데이트
- [x] `README.md`에 config 우선순위와 strategy profile 선택 방법 추가
- [x] `tests/unit/test_config_settings.py`, `test_app_main.py`, `test_strategy_factory.py` regression 추가

Exit criteria:
- YAML과 CLI에서 저장된 strategy profile을 선택할 수 있고, invalid strategy 설정은 API runtime 설정과 같은 의미로 거절된다.

## Phase 15-5. Docs and verification alignment

- [x] `docs/architecture/overview.ko.md`와 `overview.md`에 open-order authority와 audit export 상태 반영
- [x] `docs/architecture/workspace-analysis.ko.md`와 `workspace-analysis.md`의 남은 갭/권장 백로그 갱신
- [x] `docs/architecture/user-use-cases.ko.md`와 `user-use-cases.md`에 audit export와 strategy config parity 유즈케이스 추가
- [x] KIS live operations runbook에 open-order 조회 실패 대응 추가
- [x] incident response runbook에 broker order id 기반 audit 조회 절차 추가
- [x] release gate checklist에 TestClient-independent live audit 검증 항목 추가

Exit criteria:
- architecture docs와 runbook이 Phase 15 구현 후 broker pending-order, audit export, strategy config contract를 실제 코드와 일치하게 설명한다.

## Verification Checklist

### Required unit tests

- [x] `pytest tests/unit/test_kis_integration.py -q`
- [x] `pytest tests/unit/test_reconciliation.py -q`
- [x] `pytest tests/unit/test_order_audit_repository.py -q`
- [x] `pytest tests/unit/test_order_audit_routes.py -q`
- [x] `pytest tests/test_live_loop.py -q`
- [x] `pytest tests/unit/test_config_settings.py -q`
- [x] `pytest tests/unit/test_app_main.py -q`
- [x] `pytest tests/unit/test_strategy_factory.py -q`

### Required integration tests

- [x] `pytest tests/integration/test_kis_reconciliation_integration.py -q`
- [x] `pytest tests/integration/test_order_audit_integration.py -q`

### Frontend validation

- [x] `cd frontend && npm run lint`
- [x] `cd frontend && npm run build`
- [x] `cd frontend && npm run test:e2e`

### Broader regression

- [x] touched backend 범위 `ruff check`
- [x] 관련 API/config/live loop 회귀 테스트 실행
- [x] config shape 변경 후 `configs/`, `examples/`, `README.md` 동시 갱신 확인

### Manual verification

- [ ] KIS fixture 또는 sandbox 응답에서 open-order snapshot이 pending symbols를 만드는지 확인
- [ ] open-order 조회 실패 시 reconciliation이 cash/position을 변경하지 않는지 확인
- [ ] live paper session 후 `scope=live_session&owner_id={session_id}` audit record 조회
- [ ] KIS stub order id가 `/api/v1/order-audit` 응답의 `broker_order_id`에 표시되는지 확인
- [ ] audit CSV/JSONL export가 owner/time/status/broker id 필터를 적용하는지 확인
- [ ] YAML config와 CLI `--strategy-profile-id`가 같은 strategy profile을 선택하는지 확인

## Execution Log

### Date
- 2026-04-27

### Owner
- Codex

### Slice completed
- Phase 15-0: open-order contract and KIS parser
- Phase 15-1: reconciliation pending authority hardening
- Phase 15-2: broker order id audit propagation and live audit verification
- Phase 15-3: order audit filter/export
- Phase 15-4: strategy config parity
- Phase 15-5: docs and verification alignment

### Scope implemented
- Added broker open-order DTO/capability, KIS open-order query/parser, and live-loop pending-source priority.
- Propagated KIS broker order ids into fill events and order audit records.
- Extended order audit repository/API filtering and added bounded CSV/JSONL export.
- Added frontend owner-based audit export actions for run detail and live session detail.
- Added YAML strategy parser, YAML-to-AppSettings adapter, CLI `--config`, and CLI `--strategy-profile-id`.
- Updated configs, examples, README, architecture docs, KIS runbook, incident response, and release gate checklist.

### Files changed
- `src/trading_system/execution/broker.py`
- `src/trading_system/integrations/kis.py`
- `src/trading_system/execution/kis_adapter.py`
- `src/trading_system/execution/step.py`
- `src/trading_system/execution/order_audit.py`
- `src/trading_system/api/routes/order_audit.py`
- `src/trading_system/app/loop.py`
- `src/trading_system/app/main.py`
- `src/trading_system/app/settings.py`
- `src/trading_system/config/settings.py`
- `frontend/lib/api/client.ts`
- `frontend/lib/api/types.ts`
- `frontend/lib/api/backtests.ts`
- `frontend/lib/api/dashboard.ts`
- `frontend/app/runs/[runId]/page.tsx`
- `frontend/components/dashboard/SessionDetailDialog.tsx`
- `configs/base.yaml`
- `examples/sample_backtest.yaml`
- `examples/sample_backtest_krx.yaml`
- `examples/sample_live_kis.yaml`
- `README.md`
- `docs/architecture/*`
- `docs/runbooks/*` touched for KIS/order-audit/release-gate updates
- related tests under `tests/`

### Commands run
- `python -m compileall -q src/trading_system` -> passed
- `pytest tests/unit/test_kis_integration.py tests/unit/test_order_audit_repository.py tests/unit/test_order_audit_routes.py tests/test_live_loop.py tests/integration/test_order_audit_integration.py tests/unit/test_config_settings.py tests/unit/test_app_main.py -q` -> `59 passed`
- `ruff check src/trading_system tests --fix` -> fixed import formatting, then remaining long lines patched
- `ruff check src/trading_system tests` -> passed
- `pytest tests/integration/test_kis_reconciliation_integration.py tests/integration/test_order_audit_integration.py tests/test_live_loop.py -q` -> `11 passed`
- `pytest tests/unit/test_kis_integration.py tests/unit/test_reconciliation.py tests/test_live_loop.py tests/unit/test_order_audit_repository.py tests/unit/test_order_audit_routes.py tests/integration/test_kis_reconciliation_integration.py tests/integration/test_order_audit_integration.py tests/unit/test_config_settings.py tests/unit/test_app_main.py tests/unit/test_strategy_factory.py -q` -> `70 passed`
- `cd frontend && npm run lint` -> passed
- `cd frontend && npm run build` -> passed
- `cd frontend && npm run test:e2e` -> `3 passed`

### Validation results
- Backend lint, focused unit/integration tests, frontend lint/build, and Playwright smoke tests passed.
- Live owner audit is verified through direct live-loop/service-boundary integration, avoiding `TestClient(create_app())` lifespan startup.

### Risks / follow-up
- KIS open-order parser is fixture-backed and may need field mapping adjustment against a real KIS account response.
- Order audit export is bounded API response, not a background export pipeline.
- Cancel/replace and long-running open-order polling remain out of scope.
