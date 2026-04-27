# Phase 15 Implementation Plan

## Goal

Phase 15의 구현 목표는 Phase 14에서 추가된 운영 기록을 live 운영에서 신뢰 가능한 근거와 검증 가능한 contract로 보강하는 것이다. 핵심은 broker open-order authority, broker order id audit propagation, audit search/export, strategy config parity다.

핵심 구현 원칙:

1. trading decision과 risk semantics는 변경하지 않는다.
2. broker 상태가 불확실하면 포트폴리오를 조정하지 않는 fail-closed 동작을 유지한다.
3. 신규 broker capability는 optional로 두어 simulator/backtest 경로를 깨지 않는다.
4. audit export는 bounded API response로 제한한다.
5. config shape 변경은 코드, 예시, README, architecture docs를 함께 갱신한다.

## Preconditions

- Phase 14의 `OrderAuditRecord`, file/Supabase repository, `/api/v1/order-audit` route가 baseline이다.
- `LiveTradingLoop.audit_owner_id`와 `AppServices.build_live_loop(session_id=...)`는 이미 live session owner id 전달을 지원한다.
- `KisOrderResult.order_id`는 이미 존재하지만 `FillEvent`와 step audit payload에는 optional broker id 전달 경로가 없다.
- KIS 미체결 주문 조회는 실제 API 응답 차이가 있을 수 있으므로 transport fixture 기반 parser 테스트를 먼저 고정한다.
- `TestClient(create_app())` lifespan hang은 known validation risk로 취급하고, live audit 검증은 route-service boundary와 direct loop 테스트를 우선한다.

## Locked Design Decisions

### 1. Open order는 `AccountBalanceSnapshot`과 분리된 broker capability다

`AccountBalanceSnapshot`에 많은 필드를 더하지 않고, `OpenOrder`와 `OpenOrderSnapshot` DTO를 `execution.broker`에 추가한다. `BrokerSimulator` protocol에는 `get_open_orders()`를 optional capability로 추가하고, `ResilientBroker`는 delegate가 메서드를 제공할 때만 호출한다.

### 2. Reconciliation pending source 우선순위는 open orders -> balance pending signal이다

`LiveTradingLoop._maybe_reconcile()` 또는 reconciliation service 경계에서 open-order snapshot을 먼저 조회한다. open orders가 있으면 pending symbols는 open orders에서 계산한다. open-order 조회가 unsupported면 balance snapshot의 `pending_symbols`를 사용한다. open-order 조회가 supported지만 실패하면 reconciliation은 skip한다.

### 3. Broker order id는 optional `FillEvent.broker_order_id`로 전달한다

KIS adapter는 `KisOrderResult.order_id`를 `FillEvent.broker_order_id`에 넣는다. simulator는 기본 `None`을 사용한다. `execute_trading_step`의 fill event payload와 `OrderAuditRecord.broker_order_id`는 이 값을 보존한다.

### 4. Audit export는 repository list contract 확장 위에 얹는다

file/Supabase repository의 `list()` 필터를 확장하고, API route에서 CSV/JSONL 직렬화를 담당한다. DB-specific export SQL을 먼저 만들지 않는다.

### 5. YAML strategy config는 app runtime settings로 변환한다

`config.settings`는 typed YAML schema를 검증하고, 별도 helper가 `trading_system.app.settings.AppSettings`로 변환한다. CLI는 `--strategy-profile-id`를 우선 추가하고, 복잡한 inline strategy는 `--config` 또는 YAML path 흐름으로 유도한다.

## Contract Deltas

## A. Broker open-order contract

대상:
- `src/trading_system/execution/broker.py`
- `src/trading_system/execution/kis_adapter.py`
- `src/trading_system/integrations/kis.py`

필수 변화:
- `OpenOrder`와 `OpenOrderSnapshot` DTO 추가
- `get_open_orders()` optional broker capability 추가
- KIS open/unresolved order query와 parser 추가
- `ResilientBroker.get_open_orders()` resilience wrapper 추가

비고:
- KIS API 세부 응답은 fixture로 고정하고, 필수 필드가 없으면 `KisResponseError`를 발생시킨다.

## B. Reconciliation pending authority

대상:
- `src/trading_system/execution/reconciliation.py`
- `src/trading_system/app/loop.py`

필수 변화:
- reconciliation 호출 경계에 pending source metadata를 전달하거나, snapshot의 pending symbols를 open-order 결과로 대체한다.
- open-order 조회 실패 시 `portfolio.reconciliation.skipped` 또는 전용 event를 남기고 book mutation을 하지 않는다.
- open-order source와 fallback source를 structured logger payload에 포함한다.

비고:
- `reconcile()` 자체는 가능한 한 pure mutation 함수로 유지하고, broker 조회 orchestration은 live loop에 둔다.

## C. Broker order id audit propagation

대상:
- `src/trading_system/execution/broker.py`
- `src/trading_system/execution/kis_adapter.py`
- `src/trading_system/execution/step.py`
- `src/trading_system/execution/order_audit.py`

필수 변화:
- `FillEvent`에 optional `broker_order_id` 추가
- KIS fill conversion에서 order id 보존
- step fill payload에 `broker_order_id` 포함
- order audit record 변환이 해당 값을 보존

비고:
- 기존 simulator fixture는 broker id 없이 계속 통과해야 한다.

## D. Order audit filter and export contract

대상:
- `src/trading_system/execution/order_audit.py`
- `src/trading_system/api/routes/order_audit.py`
- `src/trading_system/api/schemas.py`
- `frontend/lib/api/types.ts`
- `frontend/lib/api/backtests.ts`
- `frontend/lib/api/dashboard.ts`
- `frontend/app/runs/[runId]/page.tsx`
- `frontend/components/dashboard/SessionDetailDialog.tsx`

필수 변화:
- list 필터에 `start`, `end`, `status`, `side`, `broker_order_id`, `sort` 추가
- CSV/JSONL export route 추가
- frontend owner 기준 export action 추가
- API 상한과 invalid filter validation 추가

비고:
- export는 API key middleware 뒤에 남고, public unauthenticated download URL은 만들지 않는다.

## E. Strategy config parity

대상:
- `src/trading_system/config/settings.py`
- `src/trading_system/app/settings.py`
- `src/trading_system/app/main.py`
- `src/trading_system/app/services.py`
- `configs/base.yaml`
- `examples/sample_backtest.yaml`
- `examples/sample_backtest_krx.yaml`
- `examples/sample_live_kis.yaml`
- `README.md`

필수 변화:
- YAML `strategy` section typed parser 추가
- YAML-to-runtime `AppSettings` adapter 추가
- CLI `--strategy-profile-id`와 선택적 `--config` 진입점 추가
- API와 동일한 validation semantics 재사용
- config/examples/docs 업데이트

비고:
- inline pattern strategy의 복잡한 label mapping은 YAML을 primary path로 둔다.

## Sequenced Implementation

### Step 0. Open-order contract and KIS parser

목적:
- broker가 미체결 주문을 명시적으로 제공할 수 있는 최소 contract를 만든다.

파일:
- `src/trading_system/execution/broker.py`
- `src/trading_system/execution/kis_adapter.py`
- `src/trading_system/integrations/kis.py`
- `tests/unit/test_kis_integration.py`

구체 작업:
- `OpenOrder`와 `OpenOrderSnapshot` dataclass를 추가한다.
- `ResilientBroker.get_open_orders()`를 optional delegate method로 구현한다.
- `KisApiClient.inquire_open_orders()`와 parser helper를 추가한다.
- KIS 정상 응답, 빈 응답, 필수 필드 누락, API error 테스트를 작성한다.

종료 조건:
- KIS open-order parser와 broker adapter가 fixture 기반 unit test를 통과한다.

### Step 1. Reconciliation pending authority hardening

목적:
- pending symbol 판단을 open-order source 우선으로 강화하고 불확실한 상태에서는 mutation을 막는다.

파일:
- `src/trading_system/app/loop.py`
- `src/trading_system/execution/reconciliation.py`
- `tests/unit/test_reconciliation.py`
- `tests/integration/test_kis_reconciliation_integration.py`

구체 작업:
- live loop reconciliation 전에 open-order snapshot을 조회한다.
- open orders가 있으면 balance snapshot의 pending symbols를 open-order symbols로 대체하거나 merge policy를 명시한다.
- open-order 조회 실패 시 reconciliation skip event를 남기고 book을 수정하지 않는다.
- logger payload에 `pending_source=open_orders|balance_snapshot|unsupported`를 포함한다.
- open-order source 우선순위와 fail-closed regression test를 추가한다.

종료 조건:
- pending order가 있는 심볼은 open-order source 기준으로 조정되지 않고, 조회 실패 시 cash/position이 변경되지 않는다.

### Step 2. Broker order id audit propagation and live audit verification

목적:
- 실제 broker order id가 order audit record까지 도달하고 live session owner audit이 검증되게 한다.

파일:
- `src/trading_system/execution/broker.py`
- `src/trading_system/execution/kis_adapter.py`
- `src/trading_system/execution/step.py`
- `src/trading_system/execution/order_audit.py`
- `tests/unit/test_kis_integration.py`
- `tests/unit/test_live_loop.py`
- `tests/integration/test_order_audit_integration.py`

구체 작업:
- `FillEvent.broker_order_id` optional 필드를 추가한다.
- KIS `_to_fill_event()`가 `result.order_id`를 전달하게 한다.
- step fill payload와 order audit conversion에 broker order id를 포함한다.
- direct `LiveTradingLoop` 또는 service-boundary 테스트로 `scope=live_session`, `owner_id=session_id` record 생성을 검증한다.
- audit append 실패가 live tick을 실패시키지 않는 regression test를 추가한다.

종료 조건:
- KIS order id가 audit record의 `broker_order_id`에 보존되고, live session owner audit 테스트가 TestClient 없이 통과한다.

### Step 3. Order audit filter/export

목적:
- 운영자가 owner, 시간, 상태, broker id 기준으로 audit record를 좁히고 export할 수 있게 한다.

파일:
- `src/trading_system/execution/order_audit.py`
- `src/trading_system/api/routes/order_audit.py`
- `src/trading_system/api/schemas.py`
- `frontend/lib/api/types.ts`
- `frontend/lib/api/backtests.ts`
- `frontend/lib/api/dashboard.ts`
- `frontend/app/runs/[runId]/page.tsx`
- `frontend/components/dashboard/SessionDetailDialog.tsx`
- `tests/unit/test_order_audit_repository.py`
- `tests/unit/test_order_audit_routes.py`

구체 작업:
- repository list signature와 file/Supabase filtering을 확장한다.
- API query validation과 sort direction을 추가한다.
- `/api/v1/order-audit/export` route를 CSV/JSONL bounded response로 구현한다.
- frontend API client와 owner 기준 export button/action을 추가한다.
- export content type, 필터 적용, limit 상한 테스트를 작성한다.

종료 조건:
- API가 필터링된 audit record를 CSV/JSONL로 반환하고, run/session UI에서 owner 기준 export를 요청할 수 있다.

### Step 4. Strategy config parity

목적:
- 전략 설정을 YAML/CLI/API에서 같은 의미로 사용할 수 있게 한다.

파일:
- `src/trading_system/config/settings.py`
- `src/trading_system/app/settings.py`
- `src/trading_system/app/main.py`
- `src/trading_system/app/services.py`
- `configs/base.yaml`
- `examples/sample_backtest.yaml`
- `examples/sample_backtest_krx.yaml`
- `examples/sample_live_kis.yaml`
- `README.md`
- `tests/unit/test_config_settings.py`
- `tests/unit/test_app_main.py`
- `tests/unit/test_strategy_factory.py`

구체 작업:
- YAML `strategy` section parser를 추가한다.
- parsed config를 `AppSettings`로 변환하는 helper를 추가한다.
- CLI에 `--config`와 `--strategy-profile-id`를 추가하고 우선순위를 문서화한다.
- invalid profile id, inline mapping 누락, threshold 범위 오류 테스트를 추가한다.
- config/examples/README에 strategy 설정 예시를 반영한다.

종료 조건:
- YAML과 CLI가 저장된 strategy profile을 선택할 수 있고, API runtime setting과 같은 validation 오류를 낸다.

### Step 5. Docs and verification alignment

목적:
- 새 operational contract와 검증 방식을 문서에 반영한다.

파일:
- `docs/architecture/overview.ko.md`
- `docs/architecture/overview.md`
- `docs/architecture/workspace-analysis.ko.md`
- `docs/architecture/workspace-analysis.md`
- `docs/architecture/user-use-cases.ko.md`
- `docs/architecture/user-use-cases.md`
- `docs/runbooks/kis-domestic-live-operations.ko.md`
- `docs/runbooks/kis-domestic-live-operations.md`
- `docs/runbooks/incident-response.ko.md`
- `docs/runbooks/incident-response.md`
- `docs/runbooks/release-gate-checklist.md`

구체 작업:
- architecture docs에 open-order authority와 fallback policy를 설명한다.
- user use cases에 audit export와 strategy config parity를 추가한다.
- KIS runbook에 open-order query 실패 시 운영 대응을 추가한다.
- incident response에 broker id 기반 audit 조회 절차를 추가한다.
- release gate checklist에 TestClient-independent live audit 검증 항목을 추가한다.

종료 조건:
- 문서가 Phase 15의 broker pending-order, audit export, strategy config contract를 코드와 일치하게 설명한다.

## Validation Matrix

### Required unit tests
- `pytest tests/unit/test_kis_integration.py -q`
- `pytest tests/unit/test_reconciliation.py -q`
- `pytest tests/unit/test_order_audit_repository.py -q`
- `pytest tests/unit/test_order_audit_routes.py -q`
- `pytest tests/unit/test_live_loop.py -q`
- `pytest tests/unit/test_config_settings.py -q`
- `pytest tests/unit/test_app_main.py -q`
- `pytest tests/unit/test_strategy_factory.py -q`

### Required integration tests
- `pytest tests/integration/test_kis_reconciliation_integration.py -q`
- `pytest tests/integration/test_order_audit_integration.py -q`

### Frontend validation
- `cd frontend && npm run lint`
- `cd frontend && npm run build`
- `cd frontend && npm run test:e2e`

### Manual verification
- KIS fixture 또는 sandbox 응답으로 open-order snapshot이 pending symbols를 만드는지 확인
- live paper session에서 `scope=live_session&owner_id={session_id}` audit record 조회
- KIS stub order id가 `/api/v1/order-audit` 응답의 `broker_order_id`에 나타나는지 확인
- order audit CSV/JSONL export가 owner/time/status 필터를 적용하는지 확인
- YAML config와 CLI `--strategy-profile-id`가 같은 strategy profile을 선택하는지 확인

## Recommended PR Slices

1. Open-order contract + KIS parser
2. Reconciliation pending authority hardening
3. Broker order id audit propagation + live audit tests
4. Order audit search/export + frontend owner actions
5. Strategy config parity + config/examples/README
6. Architecture docs and runbook alignment

## Risks and Fallbacks

- KIS open-order endpoint shape가 문서 또는 계좌 유형별로 다를 수 있다.

대응:
- parser를 좁고 명시적으로 작성하고, 누락 필드는 fail-closed 오류로 처리한다. 운영 확인 전에는 fallback balance pending signal을 유지한다.

- `FillEvent` optional field 추가가 많은 테스트 fixture에 영향을 줄 수 있다.

대응:
- dataclass field default를 `None`으로 두고, 기존 positional 생성 호출을 점검한다. 필요한 경우 keyword-only 전환 대신 최소 수정으로 유지한다.

- audit export가 너무 많은 데이터를 메모리에 올릴 수 있다.

대응:
- API limit 상한을 두고, 대량 export는 후속 phase의 background job으로 넘긴다.

- YAML strategy parser와 app runtime settings가 중복 검증을 만들 수 있다.

대응:
- YAML parser는 타입/shape 검증만 하고, runtime 의미 검증은 `AppSettings.validate()`를 재사용한다.

- TestClient hang으로 HTTP integration evidence가 다시 부족할 수 있다.

대응:
- live audit과 export 핵심은 route function, repository, service-boundary 테스트로 검증하고, TestClient smoke는 별도 residual risk로 기록한다.
