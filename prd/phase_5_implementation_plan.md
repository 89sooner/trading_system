# Phase 5 Implementation Plan

## Goal

Phase 5는 KIS 기반 국내주식 운영을 실제 운영에 가까운 수준으로 단단하게 만드는 단계다. 구현은 현재 KRX CSV 백테스트 경로와 KIS 라이브 경로를 유지하면서, 시세 계약, 주문 의미, 계좌 동기화, 시장 가드, 운영자 가시성을 보강한다.

가장 중요한 구현 원칙은 다음 두 가지다.

1. `src/trading_system/execution/step.py`는 계속 authoritative execution path로 유지한다.
2. 주문 상태 현실화는 브로커 통합 계층에서 해결하고, 공용 실행 경계는 보수적으로 유지한다.

## Preconditions

구현을 시작하기 전에 다음 범위를 고정한다.

- `/api/v1/live/preflight`는 Phase 5에서도 단일 심볼만 지원한다.
- 신규 dashboard route는 만들지 않는다. 기존 React `/dashboard`와 `/api/v1/dashboard/*`를 확장한다.
- 비동기 local order book, background polling loop, cancel/replace는 범위 밖이다.
- `pending_symbols`는 로컬 추정값이 아니라 broker-side unresolved/open-order 조회 결과로 생성한다.
- YAML 설정에 새 필드를 추가하면 `src/trading_system/config/settings.py`, `configs/`, `examples/`, `README.md`, 관련 테스트를 같은 변경에 함께 수정한다.

## Locked Design Decisions

### 1. Order semantics boundary

- KIS 내부 모델은 "접수됨"과 "체결됨"을 분리한다.
- 공용 브로커 계약은 계속 `submit_order(order, bar) -> FillEvent`를 사용한다.
- `FillEvent` 생성 규칙은 보수적으로 유지한다.
  - 접수 성공 + 체결수량 0: `UNFILLED`
  - 부분체결: `PARTIALLY_FILLED`
  - 전량체결: `FILLED`
- `filled_quantity > 0`일 때만 `PortfolioBook`을 변경한다.

### 2. Reconciliation safety

- `AccountBalanceSnapshot`은 최소 `cash`, `positions`, `average_costs`, `pending_symbols`를 포함하도록 확장한다.
- `pending_symbols`는 KIS unresolved/open-order 조회로부터 만들어진다.
- KIS balance snapshot은 "잔고/보유수량/평균단가 + unresolved orders"를 함께 조회할 수 있을 때만 reconciliation용 snapshot으로 간주한다.
- unresolved/open-order 조회가 실패하면 `get_account_balance()`는 safe snapshot을 반환하지 않아야 하며, live loop는 skip 이벤트를 남기고 reconcile을 수행하지 않는다.

### 3. API and frontend contract extension

- `src/trading_system/api/routes/backtest.py`의 `/api/v1/live/preflight`는 유지한다.
- `src/trading_system/api/schemas.py`의 `LivePreflightResponseDTO`를 확장해 readiness 정보를 구조화한다.
- `src/trading_system/api/routes/dashboard.py`의 기존 `status|events` payload를 선택 필드로 확장한다.
- 프론트엔드는 `frontend/src/routes/dashboard.tsx`, `frontend/src/api/dashboard.ts`, `frontend/src/api/types.ts`, `frontend/src/hooks/useDashboardPolling.ts`를 함께 수정한다.

### 4. Configuration policy

- Phase 5는 기능 구현을 위해 반드시 새로운 YAML root key를 요구하지 않는다.
- 새 설정이 API/runtime-only 입력으로 충분하면 YAML을 억지로 늘리지 않는다.
- 새 설정을 YAML에 노출할 필요가 생기면 typed loader parity와 테스트를 같은 slice에서 완료한다.

## Contract Deltas

## A. KIS quote contract

대상:
- `src/trading_system/integrations/kis.py`
- `src/trading_system/data/provider.py`

필수 변화:
- 국내주식 quote 모델을 명시적으로 정의한다.
- quote 파싱에서 0가격, 0거래량, malformed symbol, 누락 필드를 구분한다.
- quote-to-bar 변환을 독립적으로 테스트 가능한 함수/경로로 만든다.
- 샘플링 semantics를 로그와 테스트에서 설명 가능하게 만든다.

비고:
- `MarketDataProvider` 프로토콜은 유지한다.
- CSV provider 동작은 변경하지 않는다.

## B. KIS order-result contract

대상:
- `src/trading_system/integrations/kis.py`
- `src/trading_system/execution/kis_adapter.py`
- `src/trading_system/execution/broker.py`

필수 변화:
- KIS 주문 응답 모델이 order receipt metadata를 보존해야 한다.
- KIS adapter가 receipt metadata를 바탕으로 보수적 `FillEvent`를 생성해야 한다.
- 접수는 성공했지만 체결수량이 0인 경우를 명시적으로 테스트해야 한다.

비고:
- 공용 `FillEvent`는 유지한다.
- Step/strategy/risk 인터페이스는 유지한다.

## C. Broker snapshot contract

대상:
- `src/trading_system/execution/broker.py`
- `src/trading_system/execution/kis_adapter.py`
- `src/trading_system/integrations/kis.py`
- `src/trading_system/execution/reconciliation.py`
- `src/trading_system/app/loop.py`

필수 변화:
- `AccountBalanceSnapshot`에 `average_costs`를 추가한다.
- KIS adapter는 balance/holdings/average-costs와 unresolved orders를 결합해 snapshot을 만든다.
- unresolved orders 조회를 바탕으로 `pending_symbols`를 만든다.
- snapshot이 불완전하면 reconcile을 실행하지 않고 skip 이벤트를 남긴다.
- reconciliation은 `average_costs` 동기화 규칙을 명시적으로 수행한다.

명시 규칙:
- 브로커 수량이 0이면 로컬 수량과 평균단가를 제거한다.
- 브로커 수량이 양수이고 pending이 아니면 로컬 수량과 평균단가를 브로커 값으로 맞춘다.
- pending 심볼은 수량과 평균단가 모두 조정하지 않는다.

## D. Preflight and dashboard DTOs

대상:
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/routes/dashboard.py`
- `src/trading_system/api/schemas.py`
- `frontend/src/api/dashboard.ts`
- `frontend/src/api/types.ts`
- `frontend/src/hooks/useDashboardPolling.ts`
- `frontend/src/routes/dashboard.tsx`

필수 변화:
- `/api/v1/live/preflight` 응답은 문자열 message만이 아니라 readiness 필드를 제공해야 한다.
- 최소한 다음 정보가 구조화되어야 한다.
  - 실행 가능 여부
  - 실패/경고 사유 목록
  - 마지막 quote 요약 또는 점검 결과
- dashboard status payload는 필요 시 다음 선택 필드를 제공한다.
  - provider
  - symbols
  - market_session 또는 readiness summary
  - last_reconciliation_at
  - last_reconciliation_status
- event feed에는 국내주식 전용 이벤트가 포함되어야 한다.

비고:
- 신규 route는 만들지 않는다.
- 기존 프론트 route `/dashboard`만 사용한다.

## Sequenced Implementation

### Step 0. Baseline alignment

목적:
- 이후 단계에서 흔들리기 쉬운 범위를 먼저 고정한다.

구체 작업:
- `phase_5_prd.md`, `phase_5_implementation_plan.md`, `phase_5_task.md` 기준을 팀 내 합의 문서로 고정한다.
- `pending_symbols` 출처와 `/api/v1/live/preflight` 단일 심볼 유지 여부를 다시 확인한다.
- impacted file 목록에 `api/schemas.py`, React dashboard files, config tests를 포함시킨다.

종료 조건:
- 설계 모호점 없이 Step 1로 내려갈 수 있다.

### Step 1. Domestic quote contract

목적:
- quote 품질과 샘플링 semantics를 먼저 신뢰 가능하게 만든다.

파일:
- `src/trading_system/integrations/kis.py`
- `src/trading_system/data/provider.py`
- `tests/unit/test_kis_integration.py`
- `tests/unit/test_data_provider.py`

구체 작업:
- KIS quote 모델 정리
- 이상 quote validation 추가
- quote-to-bar 변환 명시화
- multi-sample load 테스트 추가

종료 조건:
- CSV 국내주식 백테스트 회귀 없음
- KIS quote parsing/validation 테스트 통과

### Step 2. Conservative order-result mapping

목적:
- 주문 접수와 체결 의미를 분리한다.

파일:
- `src/trading_system/integrations/kis.py`
- `src/trading_system/execution/kis_adapter.py`
- `src/trading_system/execution/broker.py`
- `src/trading_system/execution/step.py`
- `tests/unit/test_kis_integration.py`
- `tests/unit/test_execution_adapters_and_broker.py`

구체 작업:
- receipt metadata 포함 KIS order-result 모델 도입
- accepted-but-unfilled/partial/full/rejected 케이스 파싱
- adapter의 `FillEvent` 매핑 보수화
- `filled_quantity > 0`만 포트폴리오 반영 규칙 검증

종료 조건:
- accepted-but-unfilled가 로컬 포트폴리오를 변경하지 않음
- partial fill이 `PARTIALLY_FILLED`로 안정적으로 노출됨

### Step 3. Broker snapshot + safe reconciliation

목적:
- KIS 계좌 상태와 로컬 포트폴리오를 안전하게 비교한다.

파일:
- `src/trading_system/execution/broker.py`
- `src/trading_system/integrations/kis.py`
- `src/trading_system/execution/kis_adapter.py`
- `src/trading_system/execution/reconciliation.py`
- `src/trading_system/app/loop.py`
- `tests/unit/test_reconciliation.py`
- `tests/unit/test_live_loop_multi_symbol.py`

구체 작업:
- `average_costs`를 포함하는 snapshot 계약 확장
- KIS balance/holdings/average-costs 조회 추가
- unresolved/open-order 조회 추가
- `pending_symbols` 생성 규칙 구현
- snapshot 불완전 시 reconcile skip 이벤트 추가
- average cost 동기화 규칙 구현

종료 조건:
- drift가 있으면 이벤트가 남고, pending 심볼은 조정되지 않음
- unresolved order 조회 실패 시 로컬 포트폴리오가 변하지 않음

### Step 4. Market guards + preflight readiness

목적:
- 주문 전에 실행 가능성을 구조적으로 판단하게 만든다.

파일:
- `src/trading_system/app/services.py`
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/schemas.py`
- `src/trading_system/app/settings.py`
- `src/trading_system/config/settings.py`
- `tests/unit/test_app_services.py`
- `tests/unit/test_api_backtest_schema.py`
- `tests/unit/test_config_settings.py`
- `tests/integration/test_config_loader_integration.py`

구체 작업:
- KST 장시간 가드 추가
- 비정상 quote 가드 추가
- preflight response DTO 확장
- settings 노출 범위 결정
- YAML 노출이 필요하면 loader/test/docs 동시 수정

종료 조건:
- `live_execution=live`는 장외 시간에 차단됨
- `preflight`는 `ready`, `reasons`, quote summary를 반환함
- 설정 스키마가 문서와 테스트 기준으로 일관됨

### Step 5. Dashboard/operator surface

목적:
- 기존 operator surface로 국내주식 상태를 설명 가능하게 만든다.

파일:
- `src/trading_system/api/routes/dashboard.py`
- `src/trading_system/api/schemas.py`
- `frontend/src/api/dashboard.ts`
- `frontend/src/api/types.ts`
- `frontend/src/hooks/useDashboardPolling.ts`
- `frontend/src/routes/dashboard.tsx`
- `frontend/src/components/dashboard/StatusCard.tsx`
- `frontend/src/components/dashboard/EventFeed.tsx`
- `tests/unit/test_dashboard_routes.py`

구체 작업:
- dashboard status optional fields 추가
- event feed의 국내주식 이벤트 표시 개선
- 프론트 type/hook/status rendering 정합성 맞춤

종료 조건:
- `/dashboard`에서 quote/reconciliation 관련 상태를 볼 수 있음
- dashboard route 테스트가 DTO/행동을 검증함

### Step 6. Docs, examples, final regression

목적:
- 운영자가 Phase 5 경로를 문서만으로 재현할 수 있게 한다.

파일:
- `configs/base.yaml`
- `configs/krx_csv.yaml`
- `examples/`
- `README.md`
- `docs/runbooks/`
- `prd/phase_5_task.md`

구체 작업:
- CSV backtest -> KIS preflight -> guarded live path 문서화
- 새 설정/제약사항 문서화
- execution log와 검증 증적 업데이트

종료 조건:
- README/runbook/examples가 실제 동작과 충돌하지 않음
- task file의 검증 체크리스트가 실제 결과로 채워짐

## Validation Matrix

### Required unit tests

- `tests/unit/test_kis_integration.py`
- `tests/unit/test_data_provider.py`
- `tests/unit/test_execution_adapters_and_broker.py`
- `tests/unit/test_reconciliation.py`
- `tests/unit/test_app_services.py`
- `tests/unit/test_live_loop_multi_symbol.py`
- `tests/unit/test_dashboard_routes.py`
- `tests/unit/test_config_settings.py`
- `tests/unit/test_api_backtest_schema.py`

### Required integration tests

- `tests/integration/test_config_loader_integration.py`
- 국내주식 preflight readiness integration test 추가 및 실행
- 국내주식 reconciliation integration test 추가 및 실행

### Manual verification

- `005930` 기준 CSV 백테스트 실행
- 동일 종목 기준 KIS preflight 실행
- 장외 시간에서 `live_execution=live` 차단 확인
- accepted-but-unfilled 응답이 포트폴리오를 바꾸지 않는지 확인
- broker-side drift 시 reconciliation 이벤트 또는 skip 이벤트 확인

## Recommended PR Slices

1. Quote contract + unit tests
2. Order-result mapping + unit tests
3. Snapshot/reconciliation + unit/integration tests
4. Market guards + preflight DTO + config tests
5. Dashboard/status DTO + frontend route/types + tests
6. Docs/examples/runbooks + broad regression

## Risks and Fallbacks

- KIS unresolved/open-order API 스펙이 불안정하면 Step 3 일정이 길어질 수 있다.
- DTO 확장이 frontend 타입과 맞물리므로 API만 먼저 바꾸면 UI가 깨질 수 있다.
- YAML 설정 노출 범위를 섣불리 넓히면 `app.settings`와 `config.settings` parity 비용이 커진다.

대응:
- Step 3 이전에는 reconciliation을 KIS에서 활성화하지 않는다.
- DTO 변경은 backend schema와 frontend type을 같은 slice에서 수정한다.
- 설정 노출은 runtime/API-only가 충분한 항목부터 시작한다.
