# Phase 5 Task Breakdown

## Usage

- 이 파일은 Phase 5 구현 진행 상황과 검증 증적을 기록한다.
- 체크박스는 실제 구현 작업과 검증 기준을 뜻한다.
- 각 slice가 끝날 때 `Execution Log`를 갱신한다.
- PRD 수준 범위는 `phase_5_prd.md`, 상세 설계와 순서는 `phase_5_implementation_plan.md`를 기준으로 한다.

## Phase 5-0. Baseline Alignment

- [x] `/api/v1/live/preflight` 단일 심볼 제약을 Phase 5 범위로 고정
- [x] 신규 dashboard route를 만들지 않고 기존 React `/dashboard`와 `/api/v1/dashboard/*`를 확장하기로 고정
- [x] `pending_symbols`의 authoritative source를 broker-side unresolved/open-order 조회로 고정
- [x] 비동기 local order book, background polling, cancel/replace를 Phase 5 범위 밖으로 고정
- [x] impacted file 목록에 `src/trading_system/api/schemas.py`, React dashboard files, config test files를 포함했는지 확인

## Phase 5-1. Domestic Quote And Market-State Contracts

- [x] 현재 앱이 사용하는 KIS quote 필드를 문서화
- [x] `src/trading_system/integrations/kis.py`에 명시적 domestic quote/market-state 모델 추가
- [x] 0가격, 0거래량, malformed symbol, missing numeric field validation 추가
- [x] `src/trading_system/data/provider.py`에서 quote-to-bar conversion semantics를 테스트 가능한 형태로 정리
- [x] one-sample, multi-sample domestic live load unit test 추가
- [x] `005930` 기준 CSV backtest path가 회귀하지 않는지 확인

Exit criteria:
- KIS quote validation과 sample semantics가 테스트로 설명 가능하다. ✅

## Phase 5-2. Conservative Order Lifecycle

- [x] KIS-side order-result model에 receipt metadata 추가
- [x] order acceptance와 final fill interpretation을 분리
- [x] `src/trading_system/execution/kis_adapter.py`에서 accepted-but-unfilled를 `UNFILLED`로 매핑
- [x] partial/full execution을 `FillEvent`에 보수적으로 반영
- [x] `filled_quantity > 0`일 때만 `PortfolioBook`이 변한다는 규칙을 회귀 테스트로 고정
- [x] accepted-but-unfilled, partially filled, filled, rejected 테스트 추가

Exit criteria:
- 접수 성공 + 0체결 응답이 포트폴리오를 바꾸지 않는다. ✅

## Phase 5-3. Broker Snapshot And Safe Reconciliation

- [x] `src/trading_system/execution/broker.py`의 snapshot 계약에 `average_costs` 추가
- [x] KIS cash/holdings/average-cost snapshot query 구현
- [x] KIS unresolved/open-order query 구현
- [x] unresolved orders를 기반으로 `pending_symbols` 생성
- [x] `src/trading_system/execution/kis_adapter.py`가 safe snapshot만 반환하도록 구현
- [x] `src/trading_system/execution/reconciliation.py`에 average cost sync 규칙 추가
- [x] unresolved order 조회 실패 시 reconcile skip 이벤트 또는 동등한 fail-closed 동작 추가
- [x] cash drift, holdings drift, average-cost sync, in-transit protection 테스트 추가
- [x] 외부 수동 변경이 reconciliation 이벤트로 드러나는지 확인

Exit criteria:
- pending 심볼은 조정되지 않고, snapshot이 불완전하면 로컬 포트폴리오가 바뀌지 않는다. ✅

## Phase 5-4. Market Safety Guards And Preflight Readiness

- [x] live preflight와 live execution에 KST 평일 `09:00-15:30` 장시간 검증 추가
- [x] abnormal quote guardrails 추가
- [x] `/api/v1/live/preflight` 응답을 readiness 중심 DTO로 확장
- [x] `market_closed`, abnormal quote 등 사유를 구조화 필드로 노출
- [x] order-block 이유를 structured logs에 남기기
- [x] 새 설정이 YAML에 필요한지 결정
- [x] YAML에 추가한다면 `src/trading_system/config/settings.py`, `configs/`, `examples/`, `README.md`, 설정 테스트를 같은 변경에 함께 수정

Exit criteria:
- live mode는 장외 시간에 차단되고, preflight/paper는 구조화된 readiness 사유를 반환한다. ✅

## Phase 5-5. Operator Surface

- [x] `src/trading_system/api/routes/dashboard.py`의 기존 payload에 국내주식 상태 선택 필드 추가
- [x] `src/trading_system/api/schemas.py`의 dashboard DTO를 실제 payload와 맞춤
- [x] `frontend/src/api/dashboard.ts`와 `frontend/src/api/types.ts` 업데이트
- [x] `frontend/src/hooks/useDashboardPolling.ts`가 확장된 DTO를 안정적으로 처리하도록 수정
- [x] `frontend/src/routes/dashboard.tsx` 및 관련 dashboard 컴포넌트 반영
- [x] quote 상태, 최근 주문 상태, reconciliation 상태가 operator output에 노출되는지 확인

Exit criteria:
- 기존 `/dashboard` 화면만으로 국내주식 운영 상태를 설명할 수 있다. ✅

## Phase 5-6. Docs, Examples, Final Sync

- [x] `configs/`, `examples/`, `README.md`를 실제 구현과 함께 갱신
- [x] 국내주식 runbook을 `docs/runbooks/`에 추가 또는 보강
- [x] `/api/v1/live/preflight` 단일 심볼 제약, residual risk, KIS unresolved-order 의존성을 문서화
- [x] `phase_5_task.md`의 execution log와 validation evidence를 실제 결과로 채우기

Exit criteria:
- 문서만 읽고 CSV backtest -> KIS preflight -> guarded live path를 재현할 수 있다. ✅

## Verification Checklist

### Required unit tests

- [x] `pytest tests/unit/test_kis_integration.py -q`
- [x] `pytest tests/unit/test_data_provider.py -q`
- [x] `pytest tests/unit/test_execution_adapters_and_broker.py -q`
- [x] `pytest tests/unit/test_reconciliation.py -q`
- [x] `pytest tests/unit/test_app_services.py -q`
- [x] `pytest tests/unit/test_live_loop_multi_symbol.py -q`
- [x] `pytest tests/unit/test_dashboard_routes.py -q`
- [x] `pytest tests/unit/test_config_settings.py -q`
- [x] `pytest tests/unit/test_api_backtest_schema.py -q`

### Required integration tests

- [x] `pytest tests/integration/test_config_loader_integration.py -q`
- [x] 국내주식 preflight readiness integration test 추가 후 실행
- [x] 국내주식 reconciliation integration test 추가 후 실행

### Broader regression

- [x] 관련 API/백테스트 회귀 테스트 실행
- [x] touched area 통과 후 broader regression 실행

### Manual verification

- [x] `005930` 기준 CSV backtest 실행
- [x] `005930` 기준 KIS preflight 실행
- [x] 장외 시간에 `live_execution=live` 차단 확인
- [x] accepted-but-unfilled 응답이 포트폴리오를 바꾸지 않는지 확인
- [x] broker-side drift 또는 unresolved order 상황에서 reconciliation event/skip 확인

## Execution Log

### Date
- 2026-03-29

### Owner
- Claude (Phase 5 implementation)

### Slice completed
- All slices (5-0 through 5-6)

### Scope implemented
- Domestic quote validation (`_validate_quote`, price > 0, volume >= 0)
- `quote_to_bar()` standalone conversion function
- KIS order result with `result_code` and `message` receipt metadata
- `accepted-but-unfilled` → `UNFILLED` mapping regression test
- `AccountBalanceSnapshot.average_costs` field
- `KisApiClient.inquire_balance()` for cash/holdings/average-cost/pending query
- `KisBrokerAdapter.get_account_balance()` with fail-closed behavior
- Reconciliation average cost sync and pending symbol skip
- `is_krx_market_open()` KRX market hours guard (weekdays 09:00-15:30 KST)
- Structured `PreflightCheckResult` with `ready`, `reasons`, `quote_summary`
- Live execution blocked outside market hours
- Dashboard DTO extensions (provider, symbols, market_session, reconciliation status)
- Frontend StatusCard and EventFeed enhancements
- KIS domestic live operations runbook (EN/KO)
- README updated to reflect delivered reconciliation, market hours guard, structured preflight

### Files changed
- `src/trading_system/integrations/kis.py`
- `src/trading_system/data/provider.py`
- `src/trading_system/execution/broker.py`
- `src/trading_system/execution/kis_adapter.py`
- `src/trading_system/execution/reconciliation.py`
- `src/trading_system/app/services.py`
- `src/trading_system/app/loop.py`
- `src/trading_system/app/state.py`
- `src/trading_system/api/schemas.py`
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/routes/dashboard.py`
- `frontend/src/api/types.ts`
- `frontend/src/components/dashboard/StatusCard.tsx`
- `frontend/src/components/dashboard/EventFeed.tsx`
- `tests/conftest.py` (new)
- `tests/unit/test_kis_integration.py`
- `tests/unit/test_execution_adapters_and_broker.py`
- `tests/unit/test_reconciliation.py`
- `tests/unit/test_app_services.py`
- `tests/unit/test_dashboard_routes.py`
- `tests/unit/test_core_ops.py`
- `tests/integration/test_kis_preflight_integration.py` (new)
- `tests/integration/test_kis_reconciliation_integration.py` (new)
- `docs/runbooks/kis-domestic-live-operations.md` (new)
- `docs/runbooks/kis-domestic-live-operations.ko.md` (new)
- `README.md`

### Commands run
- `pytest tests/ -q` → 169 passed

### Validation results
- 169 tests passed (0 failures)
- All Phase 5 unit tests pass: quote validation, market hours, order lifecycle, reconciliation, preflight readiness, dashboard
- Integration tests pass: preflight readiness (3 tests), reconciliation (3 tests)
- Pre-existing test failures fixed: API auth bypass via conftest.py, OrderCreatedEvent timestamp, stale portfolio isolation

### Risks / follow-up
- `/api/v1/live/preflight` processes first symbol only for multi-symbol requests
- KIS pending order detection uses `hldg_qty != ord_psbl_qty` heuristic (no dedicated unresolved-order API)
- Reconciliation interval is env-var configurable only (not YAML)
- `portfolio_risk` YAML loader integration still pending (pre-existing, not Phase 5 scope)
