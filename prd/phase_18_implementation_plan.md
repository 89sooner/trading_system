# Phase 18 Implementation Plan

관련 문서:
- 제품 요구사항: `prd/phase_18_prd.md`
- 실행 추적: `prd/phase_18_task.md`
- 이전 phase 실행 검증: `prd/phase_17_task.md`

## Goal

Phase 18의 구현 목표는 KIS live 실거래 주문을 durable lifecycle contract로 추적하고, active/pending/stale 주문을 운영자가 API와 dashboard에서 확인하며, 취소 요청을 수행할 수 있게 하는 것이다.

핵심 구현 원칙:

1. live trading safety를 backtest 확장보다 우선한다.
2. append-only `order_audit`와 upsert 가능한 live order lifecycle state를 분리한다.
3. KIS status/cancel은 broker capability로 추가하고, capability가 없는 경로는 명시적으로 unsupported 처리한다.
4. pending/stale 주문이 있으면 신규 live 주문과 reconciliation 판단은 fail-closed할 수 있어야 한다.
5. 공통 `execution.step`의 backtest/live 매매 의미는 불필요하게 변경하지 않는다.

## Preconditions

- Phase 17의 durable backtest worker 변경은 baseline이지만 이번 phase의 핵심 범위가 아니다.
- `LiveTradingLoop`, KIS adapter, dashboard route, order audit repository가 현재 live 운영 경계다.
- `OrderAuditRepository`는 증적 로그로 유지하고 lifecycle 저장소 책임을 추가하지 않는다.
- Supabase 사용 환경은 migration 001-006 이후 migration 007을 적용해야 한다.
- frontend 변경 시 `frontend/AGENTS.md`와 기존 dashboard component 패턴을 따른다.
- 실제 KIS 운영 응답은 환경에 따라 다를 수 있으므로 parser는 보수적으로 fail-closed한다.

## Locked Design Decisions

### 1. Lifecycle state는 `src/trading_system/execution/live_orders.py`에 둔다

주문 수명주기는 execution boundary에 속한다. live loop와 API는 이 contract를 소비하고, KIS adapter는 broker 상태를 제공한다. `app` 또는 `api`에 저장소 모델을 두지 않는다.

### 2. `order_audit`는 append-only, lifecycle은 upsert source of truth로 분리한다

audit record는 “무슨 이벤트가 발생했는가”를 남긴다. lifecycle record는 “현재 주문 상태가 무엇인가”를 노출한다. dashboard와 cancel API는 lifecycle record를 기준으로 동작한다.

### 3. 취소는 idempotent request로 설계한다

cancel API는 terminal 주문에는 no-op 또는 structured validation error를 반환한다. active 주문에는 `cancel_requested=true`를 먼저 기록한 뒤 broker cancel을 시도한다. broker 호출 실패 시 요청 흔적과 error를 보존한다.

### 4. 상태 조회는 open-order snapshot 기반 resolution을 먼저 사용한다

KIS가 주문별 상세 조회를 별도로 제공하지 않거나 계정/상품 설정마다 응답이 다를 수 있으므로, 구현은 open-order snapshot으로 active 주문을 확인하고 사라진 주문은 balance/order audit와 함께 terminal 후보로 다룬다. 명확히 확인되지 않는 경우 `unknown` 또는 `stale`로 둔다.

### 5. 신규 주문 차단은 live loop 주변 gate로 구현한다

`execute_trading_step()` 내부에 broker-specific lifecycle 조회를 넣지 않는다. live loop가 tick 실행 전 active/stale 주문을 확인하고, 필요한 경우 해당 tick의 주문 제출을 차단하거나 runtime state/event로 fail-closed한다.

## Contract Deltas

## A. Live order lifecycle repository contract

대상:
- `src/trading_system/execution/live_orders.py`
- `scripts/migrations/007_add_live_order_lifecycle.sql`
- `tests/unit/test_live_order_lifecycle.py`
- `tests/unit/test_supabase_live_order_lifecycle.py`

필수 변화:
- `LiveOrderStatus`, `LiveOrderRecord`, `LiveOrderFilter`, `LiveOrderRepository` 추가
- `upsert`, `get`, `list`, `list_active`, `list_stale`, `mark_cancel_requested`, `update_from_broker` 제공
- file repository는 local lock과 atomic JSON write를 사용
- Supabase repository는 `live_order_lifecycle` table, session/status/symbol/broker_order_id index를 사용

비고:
- `broker_order_id`가 없는 paper fill도 테스트를 위해 record 생성 가능하게 하되, KIS cancel은 broker id가 있는 record만 허용한다.

## B. Broker/KIS capability contract

대상:
- `src/trading_system/execution/broker.py`
- `src/trading_system/execution/kis_adapter.py`
- `src/trading_system/integrations/kis.py`
- `tests/unit/test_kis_integration.py`

필수 변화:
- broker protocol에 optional order status/cancel capability를 추가한다.
- KIS client에 cancel request payload와 response parser를 추가한다.
- KIS open-order parser를 lifecycle status resolution에 사용할 수 있게 정규화한다.
- unsupported broker는 명확한 exception 또는 capability false로 처리한다.

비고:
- cancel/replace 중 replace는 제외한다.

## C. Live loop lifecycle sync contract

대상:
- `src/trading_system/app/loop.py`
- `src/trading_system/app/services.py`
- `src/trading_system/app/state.py`
- `tests/test_live_loop.py`

필수 변화:
- `AppServices`에 `live_order_repository` optional dependency 추가
- live loop가 order fill/audit event 이후 lifecycle record를 upsert
- active order polling interval과 stale threshold를 환경변수 또는 settings helper로 해석
- stale/pending/cancel failure를 structured runtime event로 emit
- pending/stale 주문이 있으면 신규 주문 제출 전 fail-closed gate를 적용

비고:
- gate가 strategy signal 자체를 바꾸지 않고 order submission boundary에서 동작해야 한다.

## D. API and dashboard contract

대상:
- `src/trading_system/api/routes/dashboard.py`
- `src/trading_system/api/routes/live_runtime.py`
- `src/trading_system/api/schemas.py`
- `src/trading_system/api/server.py`
- `frontend/lib/api/dashboard.ts`
- `frontend/lib/api/types.ts`
- `frontend/components/dashboard/*`
- `frontend/app/dashboard/page.tsx`
- `frontend/e2e/mocks/handlers.ts`
- `frontend/e2e/smoke.spec.ts`

필수 변화:
- active live orders list API 추가
- single order cancel API 추가
- dashboard status 또는 별도 endpoint에서 order incident summary 제공
- dashboard open orders panel과 cancel action 추가
- frontend mocks와 smoke test 갱신

비고:
- terminal order cancel action은 disabled 처리한다.

## E. Evidence and documentation contract

대상:
- `src/trading_system/api/routes/live_runtime.py`
- `src/trading_system/api/schemas.py`
- `README.md`
- `docs/architecture/*`
- `docs/runbooks/kis-domestic-live-operations*`
- `docs/runbooks/incident-response*`
- `docs/runbooks/release-gate-checklist*`

필수 변화:
- session evidence에 lifecycle summary 포함
- KIS live runbook에 order polling/cancel/stale 대응 절차 추가
- release gate에 status/cancel/stale validation 추가
- workspace analysis의 다음 backlog를 live 우선순위에 맞게 갱신

비고:
- Phase 17의 backtest worker 수동 검증 항목은 이번 phase 범위로 끌어오지 않는다.

## Sequenced Implementation

### Step 0. Lifecycle model and repository parity

목적:
- live order current-state 저장소 contract를 만들고 file/Supabase 동작을 맞춘다.

파일:
- `src/trading_system/execution/live_orders.py`
- `scripts/migrations/007_add_live_order_lifecycle.sql`
- `tests/unit/test_live_order_lifecycle.py`
- `tests/unit/test_supabase_live_order_lifecycle.py`

구체 작업:
- `LiveOrderStatus` enum과 `LiveOrderRecord` dataclass를 정의한다.
- active/terminal 상태 helper를 추가한다.
- file repository를 구현하고 index 기반 filtering을 지원한다.
- Supabase migration 007과 repository를 구현한다.
- repository parity tests로 upsert, active list, stale list, cancel request, broker update를 검증한다.

종료 조건:
- file/Supabase lifecycle repository unit tests가 같은 semantics로 통과한다.

### Step 1. KIS status and cancel capability

목적:
- KIS broker order id 기반 상태 확인과 취소 요청 capability를 추가한다.

파일:
- `src/trading_system/execution/broker.py`
- `src/trading_system/execution/kis_adapter.py`
- `src/trading_system/integrations/kis.py`
- `tests/unit/test_kis_integration.py`

구체 작업:
- broker protocol에 `cancel_order`와 status resolution capability를 추가한다.
- KIS cancel endpoint path/TR id/env override를 정의한다.
- KIS cancel payload와 response parser를 구현한다.
- open-order snapshot을 lifecycle update 입력으로 변환하는 helper를 추가한다.
- malformed response, rejected cancel, missing broker id regression tests를 추가한다.

종료 조건:
- KIS unit tests가 status/cancel success/failure/parser error를 검증한다.

### Step 2. Live loop lifecycle sync and fail-closed gate

목적:
- live loop가 주문 수명주기를 저장, polling, stale detection하고 안전하지 않은 상태에서 신규 주문을 차단한다.

파일:
- `src/trading_system/app/loop.py`
- `src/trading_system/app/services.py`
- `src/trading_system/app/state.py`
- `src/trading_system/execution/step.py`
- `tests/test_live_loop.py`

구체 작업:
- `build_services()`에서 lifecycle repository를 조립한다.
- `LiveTradingLoop`에 order polling interval/stale threshold 필드를 추가한다.
- broker order id가 있는 fill/order event를 lifecycle record로 저장한다.
- active order polling으로 remaining quantity/status/last_synced_at을 갱신한다.
- stale 또는 pending order가 있으면 runtime event를 emit하고 신규 주문 제출 전 gate를 적용한다.
- 기존 backtest와 paper loop 회귀가 깨지지 않는지 테스트한다.

종료 조건:
- live loop unit tests에서 lifecycle 생성, polling update, stale incident, pending gate가 검증된다.

### Step 3. Operator API and dashboard control

목적:
- 운영자가 active 주문을 조회하고 취소 요청할 수 있는 API/UI를 제공한다.

파일:
- `src/trading_system/api/routes/dashboard.py`
- `src/trading_system/api/routes/live_runtime.py`
- `src/trading_system/api/schemas.py`
- `src/trading_system/api/server.py`
- `tests/integration/test_live_runtime_api_integration.py`
- `frontend/lib/api/dashboard.ts`
- `frontend/lib/api/types.ts`
- `frontend/components/dashboard/*`
- `frontend/app/dashboard/page.tsx`
- `frontend/e2e/mocks/handlers.ts`
- `frontend/e2e/smoke.spec.ts`

구체 작업:
- `GET /api/v1/dashboard/orders` 또는 동등 endpoint를 추가한다.
- `POST /api/v1/dashboard/orders/{record_id}/cancel` 또는 동등 endpoint를 추가한다.
- API schema에 order lifecycle DTO와 cancel response DTO를 추가한다.
- dashboard open orders panel을 추가하고 stale/cancel state를 표시한다.
- cancel action은 terminal/unsupported 상태에서 disabled 처리한다.
- Playwright smoke와 API integration test를 갱신한다.

종료 조건:
- API와 frontend smoke에서 active order list와 cancel action rendering이 확인된다.

### Step 4. Session evidence and docs alignment

목적:
- 종료 후 리뷰와 운영 런북이 Phase 18 lifecycle/cancel/stale 동작을 설명하게 한다.

파일:
- `src/trading_system/api/routes/live_runtime.py`
- `src/trading_system/api/schemas.py`
- `README.md`
- `docs/architecture/overview.ko.md`
- `docs/architecture/overview.md`
- `docs/architecture/workspace-analysis.ko.md`
- `docs/architecture/workspace-analysis.md`
- `docs/runbooks/kis-domestic-live-operations.ko.md`
- `docs/runbooks/kis-domestic-live-operations.md`
- `docs/runbooks/incident-response.ko.md`
- `docs/runbooks/incident-response.md`
- `docs/runbooks/release-gate-checklist.ko.md`
- `docs/runbooks/release-gate-checklist.md`

구체 작업:
- session evidence response에 lifecycle record count와 recent lifecycle records를 포함한다.
- KIS runbook에 order lifecycle polling, cancel request, stale order 대응을 추가한다.
- incident runbook에 order lifecycle stale/cancel failure 시나리오를 추가한다.
- release gate checklist에 status/cancel/stale 검증을 추가한다.
- workspace analysis의 remaining gaps를 live 우선순위에 맞게 갱신한다.

종료 조건:
- 문서와 API evidence contract가 실제 구현과 일치한다.

## Validation Matrix

### Required unit tests
- `pytest tests/unit/test_live_order_lifecycle.py -q`
- `pytest tests/unit/test_supabase_live_order_lifecycle.py -q`
- `pytest tests/unit/test_kis_integration.py -q`
- `pytest tests/test_live_loop.py -q`
- `pytest tests/unit/test_api_server.py -q`

### Required integration tests
- `pytest tests/integration/test_live_runtime_api_integration.py -q`
- `pytest tests/integration/test_order_audit_integration.py -q`
- `pytest tests/integration/test_kis_reconciliation_integration.py -q`

### Frontend validation
- `cd frontend && npm run lint`
- `cd frontend && npm run build`
- `cd frontend && npm run test:e2e`

### Broader regression
- `python -m compileall -q src/trading_system`
- `ruff check src/trading_system tests`
- targeted live/backtest parity tests when `execution.step` or broker protocol changes

### Manual verification
- KIS mock/sandbox 또는 stub transport에서 open order polling이 lifecycle status를 갱신하는지 확인
- cancel request 실패 시 dashboard와 lifecycle `last_error`가 남는지 확인
- stale threshold 경과 후 latest incident와 event archive에 표시되는지 확인
- `DATABASE_URL` 환경에서 migration 007 적용 후 lifecycle repository smoke 실행

## Recommended PR Slices

1. Lifecycle model/repository/migration/tests
2. KIS status/cancel capability and parser tests
3. Live loop sync, stale detection, pending gate
4. API/dashboard visibility and cancel action
5. Evidence response and docs/release gate alignment

## Risks and Fallbacks

- KIS cancel/status 응답 필드가 문서/테스트 fixture와 다를 수 있다.

대응:
- parser는 unknown field를 허용하되 필수 식별자/수량이 없으면 fail-closed한다. live smoke에서 실제 payload 차이를 fixture로 승격한다.

- pending gate가 너무 보수적이면 paper/live tick이 자주 차단될 수 있다.

대응:
- gate reason을 structured event로 남기고, threshold/interval을 환경변수로 조정 가능하게 둔다.

- cancel request와 실제 체결이 race condition을 일으킬 수 있다.

대응:
- cancel response를 terminal truth로 보지 않고 다음 status sync가 최종 상태를 갱신하게 한다.

- dashboard cancel action이 실수로 live 주문을 취소할 수 있다.

대응:
- active session, non-terminal status, broker capability, confirmation state를 모두 확인하고 runbook에 supervised operation 전제로 문서화한다.
