# Phase 18 PRD

관련 문서:
- 이전 phase 범위/결과: `prd/phase_17_prd.md`
- 이전 phase 실행 검증: `prd/phase_17_task.md`
- 아키텍처 개요: `docs/architecture/overview.ko.md`
- 워크스페이스 분석: `docs/architecture/workspace-analysis.ko.md`
- KIS 라이브 운영 런북: `docs/runbooks/kis-domestic-live-operations.ko.md`
- 상세 구현 계획: `prd/phase_18_implementation_plan.md`
- 실행 추적: `prd/phase_18_task.md`

## 문서 목적

Phase 17은 백테스트 실행을 durable job/worker contract로 승격해 장시간 backtest 운영 가시성을 보강했다. 그러나 이 프로젝트의 우선순위는 backtest보다 실제 live 트레이드이며, 현재 live 경로에서 가장 큰 운영 리스크는 주문 제출 이후 broker 상태를 durable하게 추적하고 운영자가 개입할 수 있는 주문 수명주기 관리가 부족하다는 점이다.

현재 KIS 실주문 경로는 명시적 가드, KRX 장시간 체크, quote preflight, portfolio persistence, reconciliation, order audit를 제공한다. 하지만 order audit는 이벤트 로그이며, “현재 미체결 주문이 무엇인지”, “부분 체결 이후 남은 수량이 무엇인지”, “브로커 주문 상태 조회가 마지막으로 언제 성공했는지”, “운영자가 어떤 주문을 취소 요청했는지”를 durable한 현재 상태로 제공하지 않는다.

Phase 18은 live order lifecycle을 별도 운영 contract로 추가한다. 목표는 KIS 실거래 주문을 supervised rollout 수준에서 더 안전하게 만들기 위해 주문 receipt, 상태 polling, stale detection, cancel request, dashboard/API visibility를 하나의 end-to-end 운영 흐름으로 묶는 것이다.

## Goal

1. live 주문 제출 이후 broker order id를 기준으로 주문 수명주기 상태를 durable하게 저장한다.
2. KIS open-order/status 조회를 기반으로 pending, partially filled, filled, rejected, cancelled, stale 상태를 운영자가 확인할 수 있게 한다.
3. 운영자가 dashboard/API에서 미체결 주문을 보고 취소 요청할 수 있게 한다.
4. pending 또는 stale 주문이 있으면 portfolio reconciliation과 신규 주문 판단이 안전하게 fail-closed하도록 runtime incident를 남긴다.
5. 기존 backtest 결정성과 공통 `execution.step` 경로를 보존하고, live 전용 주문 lifecycle metadata는 execution boundary에 둔다.

이번 phase는 다음 원칙을 따른다.

- live trading safety가 backtest 확장보다 우선이다.
- order audit log와 order lifecycle state를 분리한다.
- KIS cancel/조회 기능은 capability로 추가하고, paper/mock 경로는 deterministic fake capability로 테스트한다.
- 자동 정정/자동 재주문은 하지 않는다. 운영자 취소와 상태 가시성에 집중한다.
- broker 응답 품질이 불충분하면 fill을 추정하지 않고 stale 또는 unknown 상태로 노출한다.

## Current Baseline

- `LiveTradingLoop`는 tick마다 `execute_trading_step()`을 호출하고, 처리 후 portfolio snapshot을 저장한다.
- `KisBrokerAdapter.submit_order()`는 KIS 주문 응답을 `FillEvent`로 매핑하며 `broker_order_id`를 포함할 수 있다.
- `OrderAuditRepository`는 live session scope로 `order.created`, `order.filled`, `order.rejected`, `risk.rejected` 이벤트를 저장하고 export할 수 있다.
- KIS adapter는 `get_open_orders()`와 `get_account_balance()`를 제공하며 reconciliation은 open-order snapshot을 pending authority로 우선 사용한다.
- dashboard는 live loop status, positions, events, equity, pause/resume/reset/stop control을 제공한다.
- live session history/evidence는 session metadata, order audit, archived runtime incident, equity point count를 묶어 검토할 수 있다.
- 현재 durable “현재 주문 상태” 저장소는 없다.
- KIS cancel 또는 장기 order polling workflow는 없다.
- pending order가 존재할 때 신규 주문 생성 자체를 억제하는 live 전용 gate는 명시적 contract로 분리되어 있지 않다.

## Non-Goals

- 백테스트 worker 추가 고도화, 외부 queue 도입, 부분 결과 resume
- 자동 주문 정정, 자동 재주문, smart order routing
- 복수 broker 추상화 확장 또는 KIS 외 실브로커 추가
- 완전 무인 live 운영 전환
- 복잡한 체결 allocation, tax/settlement accounting, corporate action 처리
- 실시간 websocket broker stream 도입
- RBAC 세분화 또는 인터넷 공개용 multi-tenant auth
- 전략 promotion/approval workflow

## Hard Decisions

### D-1. `order_audit`와 별도인 `live_order_lifecycle` contract를 추가한다

`order_audit`는 append-only 증적 로그로 유지한다. 운영자가 현재 미체결 주문과 마지막 broker sync 상태를 판단하려면 upsert 가능한 lifecycle record가 필요하다. 따라서 `LiveOrderRecord` 계열의 별도 저장소를 만들고, audit record에는 기존 이벤트 증적 책임만 남긴다.

### D-2. Phase 18은 취소를 구현하고 정정은 제외한다

취소는 stale 또는 의도치 않은 미체결 상태를 멈추는 최소 운영 개입이다. 정정은 가격/수량 변경, 부분 체결 잔량 처리, 재주문 정책을 포함해 실거래 리스크가 더 크므로 이번 phase에서 제외한다.

### D-3. broker 상태 polling은 live loop orchestration metadata로 둔다

주문 상태 polling 결과는 live 운영 상태와 reconciliation guard에 사용한다. 전략 signal 계산이나 backtest 결과 계산에는 연결하지 않는다. 공통 `execute_trading_step()`의 매매 의미는 유지하고, live loop 주변에서 lifecycle sync를 수행한다.

### D-4. pending/stale 주문이 있으면 신규 live 주문은 fail-closed한다

브로커와 로컬 포트폴리오 사이에 인트랜짓 주문이 있으면 같은 심볼 또는 전체 현금 상태를 신뢰하기 어렵다. Phase 18은 최소한 pending/stale 주문을 runtime incident로 노출하고, 신규 주문 제출 전 live 전용 gate에서 차단할 수 있는 구조를 만든다.

### D-5. Supabase 동시성은 migration 007의 unique/index contract로 보장한다

파일 저장소는 단일 호스트 운영용으로 보고 lock 기반 upsert를 구현한다. Supabase 저장소는 `broker_order_id`와 `session_id` 기반 unique/index 및 timestamp query를 통해 dashboard/API 조회와 polling update가 안정적으로 동작해야 한다.

## Product Requirements

### PR-1. Durable live order lifecycle model

- lifecycle record는 최소 `record_id`, `session_id`, `symbol`, `side`, `requested_quantity`, `filled_quantity`, `remaining_quantity`, `status`, `broker_order_id`, `submitted_at`, `last_synced_at`, `stale_after`, `cancel_requested`, `cancel_requested_at`, `cancelled_at`, `last_error`, `payload`를 포함해야 한다.
- 상태는 최소 `submitted`, `open`, `partially_filled`, `filled`, `rejected`, `cancel_requested`, `cancelled`, `stale`, `unknown`을 지원한다.
- file repository와 Supabase repository는 upsert/list/get/mark_cancel_requested/update_from_broker/list_active/list_stale semantics를 맞춰야 한다.
- 기존 order audit export는 깨지지 않아야 한다.

### PR-2. KIS order status and cancel capability

- KIS client는 open-order snapshot 외에 broker order id 기준 status 조회 또는 open-order 기반 status resolution을 제공해야 한다.
- KIS client는 broker order id 기준 취소 요청을 보낼 수 있어야 한다.
- KIS 응답 parser는 missing order id, malformed quantity, rejected cancel response를 구조화된 예외로 처리해야 한다.
- KIS adapter는 capability가 없는 경로와 있는 경로를 명확히 구분해야 한다.

### PR-3. Live loop order lifecycle sync

- live loop는 주문 제출 결과에서 broker order id가 있는 경우 lifecycle record를 생성 또는 갱신해야 한다.
- live loop는 configured interval로 active order를 broker 상태와 동기화해야 한다.
- status sync 실패는 portfolio를 추정 보정하지 않고 runtime event와 lifecycle `last_error`로 남겨야 한다.
- stale order는 dashboard incident와 archived runtime event로 관찰 가능해야 한다.

### PR-4. Operator cancel flow

- API는 active live session의 open/stale/cancel_requested 주문을 조회할 수 있어야 한다.
- API는 terminal order가 아닌 경우 cancel request를 기록하고 KIS cancel capability를 호출할 수 있어야 한다.
- cancel 요청이 broker 호출 실패로 끝나면 lifecycle record는 `cancel_requested` 또는 `unknown` 상태와 `last_error`를 보존해야 한다.
- paper/mock 테스트 경로에서는 deterministic fake cancel result로 회귀 테스트가 가능해야 한다.

### PR-5. Dashboard visibility and incident signaling

- dashboard는 active open orders, remaining quantity, broker order id, age, last sync freshness, stale/cancel state를 표시해야 한다.
- stale 또는 cancel 실패 주문은 latest incident와 event feed에서 눈에 띄어야 한다.
- session evidence는 lifecycle summary를 함께 노출해 종료 후 리뷰에서 order audit와 현재 주문 상태 이력을 대조할 수 있어야 한다.

### PR-6. Docs and release gates

- KIS live runbook은 order lifecycle polling, cancel flow, stale order 대응 절차를 포함해야 한다.
- release gate checklist는 첫 실주문 전 order status 조회, cancel mock/smoke, stale indicator 검증을 요구해야 한다.
- workspace analysis는 live 우선순위와 Phase 18 이후 남은 한계를 반영해야 한다.

## Scope By Epic

### Epic A. Live order lifecycle repository

목표:
- 현재 live 주문 상태를 durable하게 저장하고 조회할 수 있는 저장소 contract를 추가한다.

포함:
- lifecycle DTO/model/protocol
- file repository upsert/list/get/cancel/stale query
- Supabase migration 007 및 repository 구현
- repository parity tests

제외:
- event-sourced full order ledger
- backtest order lifecycle 저장
- broker별 schema 분기

### Epic B. KIS status and cancel capability

목표:
- KIS broker order id를 기준으로 status 확인과 취소 요청을 수행할 수 있게 한다.

포함:
- KIS cancel endpoint client method
- open-order/status parser 강화
- adapter capability method
- parser/unit tests

제외:
- order replace/correct
- websocket 체결 stream
- KIS 외 broker 구현

### Epic C. Live loop sync and fail-closed guards

목표:
- live loop에서 active order 상태를 주기적으로 동기화하고 위험한 상태를 신규 주문/reconciliation 판단에 반영한다.

포함:
- lifecycle record 생성/갱신
- polling interval 설정
- stale detection
- pending/stale incident event
- 신규 주문 전 live-only pending gate

제외:
- 자동 청산 또는 자동 재주문
- 전략 signal 억제 정책 자체의 변경
- backtest execution step 의미 변경

### Epic D. API and dashboard operator control

목표:
- 운영자가 active 주문을 보고 취소 요청할 수 있는 API/UI를 제공한다.

포함:
- active live orders list API
- order cancel API
- dashboard open orders panel
- stale/cancel state UI
- session evidence lifecycle summary

제외:
- RBAC별 cancel 권한 분리
- bulk cancel
- mobile 전용 UI

### Epic E. Docs and release gates

목표:
- 실거래 운영 절차와 검증 기준을 Phase 18 동작에 맞게 갱신한다.

포함:
- KIS live operations runbook
- incident response runbook
- release gate checklist
- architecture/workspace docs
- README 운영 주의사항

제외:
- 별도 ADR
- 외부 운영 플랫폼 문서

## Impacted Files

### Live order lifecycle contract and persistence
- `src/trading_system/execution/live_orders.py`
- `src/trading_system/execution/order_audit.py`
- `scripts/migrations/007_add_live_order_lifecycle.sql`
- `tests/unit/test_live_order_lifecycle.py`
- `tests/unit/test_supabase_live_order_lifecycle.py`

### Broker and KIS integration
- `src/trading_system/execution/broker.py`
- `src/trading_system/execution/kis_adapter.py`
- `src/trading_system/integrations/kis.py`
- `tests/unit/test_kis_integration.py`

### Live runtime and API
- `src/trading_system/app/loop.py`
- `src/trading_system/app/services.py`
- `src/trading_system/app/state.py`
- `src/trading_system/api/routes/dashboard.py`
- `src/trading_system/api/routes/live_runtime.py`
- `src/trading_system/api/schemas.py`
- `src/trading_system/api/server.py`
- `tests/test_live_loop.py`
- `tests/integration/test_live_runtime_api_integration.py`

### Frontend operator surface
- `frontend/lib/api/dashboard.ts`
- `frontend/lib/api/types.ts`
- `frontend/components/dashboard/*`
- `frontend/app/dashboard/page.tsx`
- `frontend/app/dashboard/sessions/page.tsx`
- `frontend/e2e/mocks/handlers.ts`
- `frontend/e2e/smoke.spec.ts`

### Documentation
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

## Delivery Slices

### Slice 0. Lifecycle model and repository parity
- Live order lifecycle model/protocol, file repository, Supabase migration/repository, parity tests를 추가한다.

### Slice 1. KIS status/cancel capability
- KIS status resolution과 cancel request parser/client/adapter method를 구현한다.

### Slice 2. Live loop sync and stale detection
- 주문 제출 결과를 lifecycle record로 저장하고, active order polling과 stale incident를 live loop에 연결한다.

### Slice 3. Operator API and dashboard control
- active order list/cancel API와 dashboard open order panel/cancel action을 추가한다.

### Slice 4. Evidence, docs, and release gates
- session evidence와 운영 문서를 lifecycle/cancel/stale workflow에 맞게 갱신한다.

## Success Metrics

- unit test에서 lifecycle repository file/Supabase semantics가 동일하게 검증된다.
- KIS parser tests가 order status, open order, cancel success/failure를 다룬다.
- live loop test에서 broker order id가 있는 fill이 lifecycle record를 만들고, stale order가 incident로 남는다.
- API integration test에서 active order list와 cancel request가 검증된다.
- dashboard smoke에서 open order panel과 cancel action rendering이 통과한다.
- KIS live runbook과 release gate checklist가 첫 실주문 전 lifecycle/cancel 검증을 요구한다.

## Risks and Follow-up

- KIS cancel/status endpoint field가 실제 운영 응답과 다를 수 있다. 초기 구현은 parser를 보수적으로 만들고 live smoke에서 필드 차이를 기록해야 한다.
- cancel request 이후 broker가 이미 체결시킨 주문은 cancelled가 아니라 filled/partially_filled로 끝날 수 있다. UI와 runbook은 이를 정상 race condition으로 설명해야 한다.
- stale detection threshold가 너무 짧으면 false positive가 늘 수 있다. 환경변수 또는 설정값으로 조정 가능하게 둔다.
- Phase 18 이후에는 bulk cancel, replace/correct, broker stream, 더 강한 auth/RBAC를 별도 phase로 검토한다.
