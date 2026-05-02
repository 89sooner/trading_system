# Phase 18 Task Breakdown

## Usage

- 이 파일은 Phase 18 구현 진행 상황과 검증 증적을 기록한다.
- 체크박스는 실제 구현 작업과 검증 기준을 뜻한다.
- 각 slice가 끝날 때 `Execution Log`를 갱신한다.
- PRD 수준 범위는 `phase_18_prd.md`를 기준으로 한다.
- 상세 설계와 순서는 `phase_18_implementation_plan.md`를 기준으로 한다.

## Status Note

- 이 문서는 `prd/phase_18_prd.md`의 실행 추적 문서다.
- 현재 체크박스는 active backlog를 slice 단위로 분해한 것이며, 아직 구현 완료를 의미하지 않는다.
- 이번 phase의 핵심은 live order lifecycle, KIS status/cancel capability, active order polling, stale detection, operator cancel visibility다.

## Phase 18-0. Lifecycle model and repository parity

- [x] `LiveOrderStatus`, `LiveOrderRecord`, `LiveOrderFilter`, `LiveOrderRepository` contract 추가
- [x] file repository upsert/get/list/list_active/list_stale 구현
- [x] file repository cancel request와 broker update transition 구현
- [x] Supabase migration `007_add_live_order_lifecycle.sql` 작성
- [x] Supabase repository upsert/get/list/list_active/list_stale 구현
- [x] Supabase repository cancel request와 broker update transition 구현
- [x] active/terminal/stale 상태 helper 테스트 추가
- [x] file/Supabase repository parity 테스트 추가

Exit criteria:
- 저장소별 lifecycle unit tests가 같은 upsert/list/cancel/stale semantics로 통과한다.

## Phase 18-1. KIS status and cancel capability

- [x] broker protocol에 order status/cancel capability 추가
- [x] KIS cancel endpoint path, TR id, env override 정의
- [x] KIS cancel request payload 생성 구현
- [x] KIS cancel response parser 구현
- [x] KIS open-order snapshot을 lifecycle status update 입력으로 변환
- [x] unsupported broker capability 처리 경로 구현
- [x] cancel success/failure parser unit tests 추가
- [x] malformed open-order/status response regression tests 추가

Exit criteria:
- KIS unit tests가 status/cancel success, rejected cancel, malformed payload, unsupported capability를 검증한다.

## Phase 18-2. Live loop lifecycle sync and fail-closed gate

- [x] `AppServices`에 live order lifecycle repository dependency 추가
- [x] `build_services()`에서 file/Supabase lifecycle repository 조립
- [x] `LiveTradingLoop`에 order polling interval과 stale threshold 설정 추가
- [x] broker order id가 있는 live order 결과를 lifecycle record로 저장
- [x] active order polling으로 remaining/status/last_synced_at 갱신
- [x] polling 실패 시 lifecycle `last_error`와 runtime event 기록
- [x] stale order 감지 시 dashboard incident 대상 event emit
- [x] pending/stale 주문이 있을 때 신규 live 주문을 fail-closed하는 gate 추가
- [x] live loop unit tests로 lifecycle 생성, polling update, stale incident, pending gate 검증

Exit criteria:
- live loop test에서 lifecycle 저장, 상태 동기화, stale 감지, pending gate가 결정적으로 검증된다.

## Phase 18-3. Operator API and dashboard control

- [x] API schema에 live order lifecycle DTO 추가
- [x] active live order list endpoint 추가
- [x] single order cancel endpoint 추가
- [x] terminal/unsupported cancel 요청 처리 contract 고정
- [x] API integration test에서 active list와 cancel request 검증
- [x] frontend API type/client 갱신
- [x] dashboard open orders panel 추가
- [x] stale/cancel_requested/cancel_failed 상태 표시 추가
- [x] cancel action disabled/confirmation 상태 구현
- [x] Playwright smoke에 open orders panel과 cancel action rendering 추가

Exit criteria:
- API와 frontend에서 active 주문 상태와 cancel action을 확인할 수 있고 smoke test가 통과한다.

## Phase 18-4. Session evidence and docs alignment

- [x] live runtime session evidence에 lifecycle summary 추가
- [x] evidence DTO와 route tests 갱신
- [x] KIS live operations runbook에 order lifecycle polling 절차 추가
- [x] KIS live operations runbook에 cancel request와 stale order 대응 절차 추가
- [x] incident response runbook에 order lifecycle stale/cancel failure 시나리오 추가
- [x] release gate checklist에 status/cancel/stale 검증 추가
- [x] architecture/workspace docs에 Phase 18 live 우선순위와 남은 한계 반영
- [x] README 운영 주의사항과 migration 007 안내 갱신

Exit criteria:
- session evidence와 운영 문서가 Phase 18 구현 후 live order lifecycle 동작을 실제 코드와 일치하게 설명한다.

## Verification Checklist

### Required unit tests

- [x] `pytest tests/unit/test_live_order_lifecycle.py -q`
- [x] `pytest tests/unit/test_supabase_live_order_lifecycle.py -q`
- [x] `pytest tests/unit/test_kis_integration.py -q`
- [x] `pytest tests/test_live_loop.py -q`
- [x] `pytest tests/unit/test_api_server.py -q`

### Required integration tests

- [x] `pytest tests/integration/test_live_runtime_api_integration.py -q`
- [x] `pytest tests/integration/test_order_audit_integration.py -q`
- [x] `pytest tests/integration/test_kis_reconciliation_integration.py -q`

### Frontend validation

- [x] `cd frontend && npm run lint`
- [x] `cd frontend && npm run build`
- [x] `cd frontend && npm run test:e2e`

### Broader regression

- [x] `python -m compileall -q src/trading_system`
- [x] `ruff check src/trading_system tests`
- [x] touched area 통과 후 live/backtest parity 회귀 테스트 실행

### Manual verification

- [ ] KIS mock/sandbox 또는 stub transport에서 open order polling이 lifecycle status를 갱신하는지 확인
- [ ] cancel request 실패 시 dashboard와 lifecycle `last_error`가 남는지 확인
- [ ] stale threshold 경과 후 latest incident와 event archive에 표시되는지 확인
- [ ] pending/stale 주문이 있는 상태에서 신규 live 주문 gate가 fail-closed하는지 확인
- [ ] `DATABASE_URL` 환경에서 migration 007 적용 후 lifecycle repository smoke 실행

## Execution Log

### Date
- 2026-05-02

### Owner
- Codex

### Slice completed
- Phase 18-0: lifecycle model and repository parity
- Phase 18-1: KIS status and cancel capability
- Phase 18-2: live loop lifecycle sync and fail-closed gate
- Phase 18-3: operator API and dashboard control
- Phase 18-4: session evidence and docs alignment

### Scope implemented
- Added durable live order lifecycle records with file/Supabase repository implementations and migration 007.
- Added broker cancel capability and KIS cancel request/response parsing.
- Wired live loop order polling, stale detection, cancel error preservation, reconciliation skip, and fail-closed tick gate.
- Added dashboard active order list/cancel APIs, evidence lifecycle summary, frontend Open orders panel, and Playwright coverage.
- Updated README, KIS runbooks, incident response, release gate checklist, and workspace analysis.

### Files changed
- `src/trading_system/execution/live_orders.py`
- `scripts/migrations/007_add_live_order_lifecycle.sql`
- `src/trading_system/execution/broker.py`
- `src/trading_system/execution/kis_adapter.py`
- `src/trading_system/integrations/kis.py`
- `src/trading_system/app/loop.py`
- `src/trading_system/app/services.py`
- `src/trading_system/api/routes/dashboard.py`
- `src/trading_system/api/routes/live_runtime.py`
- `src/trading_system/api/schemas.py`
- `src/trading_system/api/server.py`
- `frontend/components/dashboard/OpenOrdersPanel.tsx`
- `frontend/app/dashboard/page.tsx`
- `frontend/hooks/useDashboardPolling.ts`
- `frontend/hooks/useDashboardStream.ts`
- `frontend/lib/api/dashboard.ts`
- `frontend/lib/api/types.ts`
- `tests/unit/test_live_order_lifecycle.py`
- `tests/unit/test_supabase_live_order_lifecycle.py`
- `tests/unit/test_kis_integration.py`
- `tests/test_live_loop.py`
- `tests/integration/test_live_runtime_api_integration.py`
- `README.md`
- `docs/architecture/workspace-analysis*.md`
- `docs/runbooks/kis-domestic-live-operations*.md`
- `docs/runbooks/incident-response*.md`
- `docs/runbooks/release-gate-checklist*.md`

### Commands run
- `python -m compileall -q src/trading_system` -> passed
- `pytest tests/unit/test_live_order_lifecycle.py tests/unit/test_supabase_live_order_lifecycle.py tests/unit/test_kis_integration.py tests/test_live_loop.py tests/integration/test_live_runtime_api_integration.py tests/unit/test_api_server.py -q` -> `46 passed`
- `pytest tests/integration/test_order_audit_integration.py tests/integration/test_kis_reconciliation_integration.py -q` -> `7 passed`
- `ruff check src/trading_system tests` -> passed
- `cd frontend && npm run lint` -> passed
- `cd frontend && npm run build` -> passed
- `cd frontend && npm run test:e2e` -> `5 passed`

### Validation results
- File lifecycle repository upsert/list/stale/cancel transitions are covered.
- KIS cancel success and rejection parser paths are covered with stub transports.
- Live loop lifecycle polling, partial fill update, and active order gate are covered.
- Dashboard order list/cancel route is covered through integration-level direct route tests.
- Frontend Open orders panel renders in Playwright smoke.

### Risks / follow-up
- Supabase migration 007 and repository methods are implemented but not verified against a live Supabase database in this environment.
- KIS cancel request fields are parser-tested with fixtures; a sandbox or supervised small-order smoke should confirm the exact production payload/response shape before relying on it operationally.
