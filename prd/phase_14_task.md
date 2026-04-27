# Phase 14 Task Breakdown

## Usage

- 이 파일은 Phase 14 구현 진행 상황과 검증 증적을 기록한다.
- 체크박스는 실제 구현 작업과 검증 기준을 뜻한다.
- 각 slice가 끝날 때 `Execution Log`를 갱신한다.
- PRD 수준 범위는 `phase_14_prd.md`를 기준으로 한다.
- 상세 설계와 순서는 `phase_14_implementation_plan.md`를 기준으로 한다.

## Status Note

- 이 문서는 `prd/phase_14_prd.md`의 실행 추적 문서다.
- 현재 체크박스는 active backlog를 slice 단위로 분해한 것이며, 아직 구현 완료를 의미하지 않는다.
- 이번 phase의 핵심은 session history UX, order audit persistence, queue/retention 운영 가시성이다.

## Phase 14-0. Live session history UX

- [x] `frontend/lib/api/types.ts`에 live runtime session list/detail 타입 추가
- [x] `frontend/lib/api/dashboard.ts`에 session list/detail client 함수 추가
- [x] `frontend/components/dashboard/SessionHistoryPanel.tsx` 신규 작성
- [x] `frontend/components/dashboard/SessionDetailDialog.tsx` 신규 작성
- [x] `frontend/app/dashboard/page.tsx`에 session history panel 연결
- [x] session history loading/empty/error 상태 처리
- [x] frontend smoke/e2e mock에 session history 응답 추가

Exit criteria:
- dashboard에서 최근 live session 목록을 볼 수 있고, session detail dialog에서 preflight summary와 종료 상태를 확인할 수 있다.

## Phase 14-1. Order audit DTO/repository/migration 추가

- [x] `src/trading_system/execution/order_audit.py`에 `OrderAuditRecord`와 repository protocol 정의
- [x] file 기반 order audit repository 구현
- [x] Supabase 기반 order audit repository 구현
- [x] `create_order_audit_repository()` factory 추가
- [x] `src/trading_system/api/schemas.py`에 order audit DTO 추가
- [x] `src/trading_system/api/routes/order_audit.py` 신규 route 추가
- [x] `src/trading_system/api/server.py`에 order audit repository와 router 연결
- [x] `scripts/migrations/004_add_order_audit_records.sql` 작성

Exit criteria:
- order audit record를 file/Supabase 저장소에 저장하고 API로 필터 조회할 수 있다.

## Phase 14-2. Backtest/live audit wiring

- [x] audit sink interface 또는 optional callback을 trading 실행 경계에 추가
- [x] `execute_trading_step`의 order/risk event를 audit record로 변환하는 helper 추가
- [x] 백테스트 실행 경로가 `run_id`를 audit owner id로 전달
- [x] live runtime 실행 경로가 `session_id`를 audit owner id로 전달
- [x] audit 저장 실패가 백테스트 결과와 live loop 상태를 바꾸지 않도록 처리
- [x] backtest owner 기준 order audit integration test 추가
- [ ] live session owner 기준 order audit integration test 추가

Exit criteria:
- 백테스트 run과 live session에서 발생한 주문 생성/체결/거절/리스크 거절이 owner id 기준으로 조회된다.

## Phase 14-3. Queue status와 retention operations 추가

- [x] `BacktestRunDispatcher`에 status snapshot 추가
- [x] dispatcher status API endpoint 추가
- [x] file/Supabase repository의 `list/delete` contract를 조합하는 retention preview/prune API 구현
- [x] prune API가 explicit confirm 없이는 거절되도록 구현
- [x] `frontend/lib/api/backtests.ts`에 dispatcher/retention client 추가
- [x] `frontend/app/runs/page.tsx`에 queue status와 retention 최소 UI 추가
- [x] cutoff/status 기준 preview/prune 테스트 추가

Exit criteria:
- 운영자가 run queue 상태를 확인하고, preview 후 confirm을 통해 오래된 run 기록을 정리할 수 있다.

## Phase 14-4. Docs and runbook alignment

- [x] `docs/architecture/overview.ko.md`와 `overview.md` 업데이트
- [x] `docs/architecture/workspace-analysis.ko.md`와 `workspace-analysis.md` 업데이트
- [x] `docs/architecture/user-use-cases.ko.md`와 `user-use-cases.md` 업데이트
- [x] `docs/runbooks/deploy-production.ko.md`와 `deploy-production.md`에 migration 절차 추가
- [x] architecture docs에서 백테스트 실행 모델을 current async dispatcher 기준으로 정정

Exit criteria:
- architecture docs와 runbook이 Phase 14의 session history UX, order audit, queue/retention contract를 실제 코드와 일치하게 설명한다.

## Verification Checklist

### Required unit tests

- [x] `pytest tests/unit/test_order_audit_repository.py -q`
- [x] `pytest tests/unit/test_order_audit_routes.py -q`
- [x] `pytest tests/unit/test_backtest_dispatcher.py -q`
- [x] `pytest tests/unit/test_backtest_retention_routes.py -q`
- [x] `pytest tests/unit/test_file_repository.py -q`
- [x] `pytest tests/unit/test_supabase_repository.py -q`
- [x] `pytest tests/unit/test_backtest_engine.py -q`
- [x] `pytest tests/test_live_loop.py -q`

### Required integration tests

- [x] `pytest tests/integration/test_order_audit_integration.py -q`
- [ ] `pytest tests/integration/test_backtest_run_api_integration.py -q`
- [ ] `pytest tests/integration/test_live_runtime_api_integration.py -q`

### Broader regression

- [x] touched backend 범위 `ruff check`
- [ ] `pytest --tb=short -q`
- [x] `cd frontend && npm run lint`
- [x] `cd frontend && npm run build`
- [x] `cd frontend && npm run test:e2e`

### Manual verification

- [ ] dashboard에서 recent live session 목록과 detail dialog 확인
- [ ] 백테스트 실행 후 backtest owner 기준 order audit 조회
- [ ] live paper session start/stop 후 live session owner 기준 order audit 조회
- [ ] retention preview가 실제 삭제 없이 후보만 반환하는지 확인
- [ ] confirm 없는 prune 요청이 거절되는지 확인
- [ ] confirm 있는 prune 요청이 cutoff/status 조건에 맞는 대상만 삭제하는지 확인

## Execution Log

### Date
- 2026-04-27

### Owner
- Codex

### Slice completed
- Phase 14-0: live session history UX
- Phase 14-1: order audit DTO/repository/migration
- Phase 14-2: backtest/live audit wiring, except live-session integration evidence
- Phase 14-3: dispatcher status and retention operations
- Phase 14-4: architecture docs and deploy runbook alignment

### Scope implemented
- Dashboard recent live session panel and detail dialog.
- Durable order audit repository for file/Supabase, API route, migration, and backtest/live audit owner wiring.
- Backtest dispatcher status endpoint and cutoff/status retention preview/prune endpoint with explicit `DELETE` confirmation.
- Runs page dispatcher and retention controls.
- Architecture docs and deployment migration notes updated for dispatcher/order audit/session history.

### Files changed
- `src/trading_system/execution/order_audit.py`
- `src/trading_system/api/routes/order_audit.py`
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/schemas.py`
- `src/trading_system/api/server.py`
- `src/trading_system/app/services.py`
- `src/trading_system/app/loop.py`
- `src/trading_system/backtest/engine.py`
- `src/trading_system/backtest/dispatcher.py`
- `src/trading_system/execution/step.py`
- `frontend/app/dashboard/page.tsx`
- `frontend/app/runs/page.tsx`
- `frontend/components/dashboard/SessionHistoryPanel.tsx`
- `frontend/components/dashboard/SessionDetailDialog.tsx`
- `frontend/lib/api/backtests.ts`
- `frontend/lib/api/dashboard.ts`
- `frontend/lib/api/types.ts`
- `scripts/migrations/004_add_order_audit_records.sql`
- `docs/architecture/*.md`
- `docs/runbooks/deploy-production*.md`
- order audit and retention related tests

### Commands run
- `ruff check ...` touched backend/test files -> passed
- `pytest tests/unit/test_order_audit_repository.py tests/unit/test_order_audit_routes.py tests/unit/test_backtest_engine.py -q` -> `12 passed`
- `pytest tests/unit/test_order_audit_repository.py tests/unit/test_order_audit_routes.py tests/unit/test_backtest_engine.py tests/unit/test_backtest_dispatcher.py tests/unit/test_backtest_retention_routes.py tests/unit/test_file_repository.py tests/unit/test_supabase_repository.py tests/integration/test_order_audit_integration.py tests/test_live_loop.py -q` -> `53 passed, 1 skipped`
- `pytest tests/unit/test_backtest_retention_routes.py -q` -> `2 passed`
- `pytest tests/test_live_loop.py -q` -> `2 passed`
- `cd frontend && npm run lint` -> passed
- `cd frontend && npm run build` -> passed
- `cd frontend && npm run test:e2e` -> `3 passed`
- `timeout 20s pytest tests/integration/test_order_audit_integration.py -q` before rewriting TestClient usage -> timed out due `TestClient(create_app())` environment hang

### Validation results
- Backend lint and focused unit/integration tests passed after replacing the new order-audit integration test with direct route/repository boundary verification.
- Frontend lint, production build, and Playwright smoke tests passed.
- `TestClient(create_app())` still hangs in this environment at app lifespan entry, matching prior Phase 13 validation risk; TestClient-heavy integration suites were not re-run successfully.

### Risks / follow-up
- live session owner audit wiring is implemented via `LiveTradingLoop.audit_owner_id`, but a live-session order audit integration test remains open because `TestClient(create_app())` hangs in this environment.
- Retention is implemented as an API service over repository `list/delete`, not as dedicated repository pruning methods.
- Order audit captures step-level order/risk events; broker-specific unresolved-order polling and cancel/replace workflows remain out of scope.
