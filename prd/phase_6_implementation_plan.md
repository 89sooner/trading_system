# Phase 6 Implementation Plan

## Goal

Phase 6는 Phase 5 종료 후 남은 운영 공백 4개를 구현 가능한 backlog로 전환하는 단계다. 구현은 현재의 multi-symbol live/backtest baseline을 유지하면서, preflight contract, pending-order detection, 설정 parity, 문서 기준선을 서로 충돌 없이 맞추는 데 집중한다.

가장 중요한 구현 원칙은 다음 네 가지다.

1. 기존 `/api/v1/live/preflight`와 `step.py` 중심 실행 경로를 가능한 한 유지한다.
2. pending order 보호 규칙은 더 강한 브로커 근거로 보강하되, 불확실할 때는 fail-closed를 유지한다.
3. 설정을 YAML에 노출하면 loader/test/docs parity를 같은 변경에서 닫는다.
4. historical task 문서 정리는 히스토리를 지우는 작업이 아니라 active backlog 기준선을 명확히 하는 작업이다.

## Preconditions

구현을 시작하기 전에 다음 범위를 고정한다.

- Phase 6 구현 범위는 `phase_6_prd.md`에 명시된 4개 잔여 리스크와 task-document hygiene에 한정한다.
- 신규 자산군, 신규 브로커, async order-state machine, cancel/replace, streaming 도입은 범위 밖이다.
- multi-symbol preflight를 다루더라도 가능하면 기존 `/api/v1/live/preflight` 경로를 유지한다.
- `TRADING_SYSTEM_RECONCILIATION_INTERVAL`, `portfolio_risk`를 YAML에 노출하면 `src/trading_system/config/settings.py`, `configs/`, `examples/`, `README.md`, 관련 테스트를 같은 slice에 포함한다.
- `phase_3_task.md`, `phase_4_task.md`, `phase_5_task.md`는 historical record로 유지하며 대규모 개편은 하지 않는다.

## Locked Design Decisions

### 1. Multi-symbol preflight는 기존 endpoint를 우선 확장한다

- `/api/v1/live/preflight`는 새 route를 추가하기보다 기존 contract를 확장하는 방향을 우선 검토한다.
- multi-symbol 응답은 최소한 심볼별 readiness 판단을 설명할 수 있어야 한다.
- 단일 readiness 표현과의 backward compatibility를 고려해 DTO를 설계한다.

### 2. Pending-order detection은 휴리스틱-only 상태를 종료한다

- `pending_symbols`는 가능하면 전용 unresolved/open-order source를 authoritative source로 사용한다.
- 전용 source가 부족할 때만 휴리스틱 fallback을 허용하며, fallback 사용 조건은 문서/테스트에 명시한다.
- source가 불충분하면 reconciliation은 skip 또는 fail-closed 경로를 유지한다.

### 3. Configuration parity는 loader/docs/tests를 함께 닫는다

- `TRADING_SYSTEM_RECONCILIATION_INTERVAL` YAML 지원과 `portfolio_risk` YAML loader integration은 같은 범주의 parity 작업으로 본다.
- 설정 shape가 바뀌면 `config.settings`, config examples, operator docs, integration/unit tests를 함께 수정한다.
- runtime/API-only 지원과 YAML 지원을 혼용한 half-supported 상태를 남기지 않는다.

### 4. 문서 정리는 active backlog source를 고정하는 수준으로 제한한다

- `phase_6_prd.md`, `phase_6_task.md`, `phase_6_implementation_plan.md`를 active backlog source로 사용한다.
- 과거 task 문서의 execution log와 체크리스트는 삭제하지 않는다.
- 필요하면 status note나 cross-link만 추가한다.

## Contract Deltas

## A. Live preflight request/response contract

대상:
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/schemas.py`
- 관련 operator docs and examples

필수 변화:
- multi-symbol 요청 처리 방식을 명확히 정의한다.
- readiness 결과를 심볼별 또는 aggregate+detail 구조로 표현할 수 있게 한다.
- 기존 단일 심볼 소비자와의 호환 규칙을 정리한다.

비고:
- 기존 endpoint path는 유지하는 방향을 우선 검토한다.

## B. Pending order detection contract

대상:
- `src/trading_system/integrations/kis.py`
- `src/trading_system/execution/kis_adapter.py`
- `src/trading_system/execution/reconciliation.py`

필수 변화:
- `pending_symbols` 생성 source 우선순위를 명확히 한다.
- 휴리스틱 fallback 조건을 제한한다.
- source가 부족하면 reconciliation을 fail-closed 하도록 규칙을 고정한다.

비고:
- full async order tracking은 Phase 6 범위 밖이다.

## C. Configuration loader contract

대상:
- `src/trading_system/config/settings.py`
- `src/trading_system/app/settings.py`
- `configs/base.yaml`
- `examples/`

필수 변화:
- `TRADING_SYSTEM_RECONCILIATION_INTERVAL` YAML 설정 경로 정의
- `portfolio_risk` typed loader support 정의
- env-var override precedence 문서화

비고:
- operator docs와 실제 loader behavior가 어긋나지 않아야 한다.

## D. Documentation/status contract

대상:
- `README.md`
- `prd/phase_6_prd.md`
- `prd/phase_6_task.md`
- `prd/phase_3_task.md`
- `prd/phase_4_task.md`
- `prd/phase_5_task.md`

필수 변화:
- active backlog source와 historical record를 구분하는 문구 유지
- README roadmap과 phase docs가 동일한 backlog 표현을 쓰도록 맞춤

## Sequenced Implementation

### Step 0. Backlog and document alignment

목적:
- 구현 전에 active backlog source를 고정하고 historical 문서 해석 기준을 정리한다.

파일:
- `prd/phase_6_prd.md`
- `prd/phase_6_task.md`
- `prd/phase_3_task.md`
- `prd/phase_4_task.md`
- `prd/phase_5_task.md`
- `README.md`

구체 작업:
- Phase 5 follow-up 4개를 Phase 6 active backlog로 고정
- older phase task 문서의 status note와 cross-link 점검
- roadmap wording과 phase docs의 terminology 동기화

종료 조건:
- 현재 backlog source가 `phase_6_prd.md`, `phase_6_task.md`, `phase_6_implementation_plan.md`로 명확히 고정된다.

### Step 1. Multi-symbol preflight contract

목적:
- live preflight의 심볼 처리 범위를 실제 멀티심볼 baseline과 맞춘다.

파일:
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/schemas.py`
- `tests/unit/test_api_backtest_schema.py`
- 관련 integration tests
- `README.md`

구체 작업:
- 기존 preflight 요청/응답 contract 분석
- multi-symbol 처리 정책 결정
- readiness DTO의 aggregate/detail 구조 정의
- backward compatibility 기준 문서화

종료 조건:
- multi-symbol preflight contract가 테스트와 문서 기준으로 설명 가능하다.

### Step 2. Pending order source hardening

목적:
- `pending_symbols` 보호 규칙을 더 신뢰 가능한 source에 연결한다.

파일:
- `src/trading_system/integrations/kis.py`
- `src/trading_system/execution/kis_adapter.py`
- `src/trading_system/execution/reconciliation.py`
- `tests/unit/test_execution_adapters_and_broker.py`
- `tests/unit/test_reconciliation.py`
- 관련 integration tests

구체 작업:
- unresolved/open-order source capability 재검토
- 휴리스틱 fallback 사용 조건 고정
- insufficient-source 시 skip/fail-closed 동작 유지
- regression test 보강

종료 조건:
- pending-order detection source와 fallback 정책이 테스트/문서 기준으로 일관된다.

### Step 3. Configuration parity recovery

목적:
- reconciliation interval과 `portfolio_risk`의 설정 경로를 실제 loader 동작과 일치시킨다.

파일:
- `src/trading_system/config/settings.py`
- `src/trading_system/app/settings.py`
- `configs/base.yaml`
- `examples/`
- `README.md`
- `tests/unit/test_config_settings.py`
- `tests/integration/test_config_loader_integration.py`

구체 작업:
- `TRADING_SYSTEM_RECONCILIATION_INTERVAL` YAML schema 추가 여부 확정
- `portfolio_risk` typed loader integration 구현
- env-var/YAML precedence 정책 문서화
- examples/config/tests 동시 갱신

종료 조건:
- 설정 경로가 loader/docs/tests에서 서로 충돌하지 않는다.

### Step 4. Final doc sync and closure prep

목적:
- 구현 결과와 운영 문서, task 기록, residual follow-up을 하나의 기준선으로 정리한다.

파일:
- `README.md`
- `docs/runbooks/` 관련 문서
- `prd/phase_6_task.md`

구체 작업:
- operator-facing docs 최종 점검
- execution log와 validation evidence 업데이트
- closure criteria 충족 여부 기록

종료 조건:
- 문서만 읽고 Phase 6 active backlog, 설정 제약, 운영 제약을 혼동 없이 설명할 수 있다.

## Validation Matrix

### Required unit tests

- `tests/unit/test_config_settings.py`
- `tests/unit/test_execution_adapters_and_broker.py`
- `tests/unit/test_reconciliation.py`
- `/api/v1/live/preflight` multi-symbol contract 관련 unit test

### Required integration tests

- `tests/integration/test_config_loader_integration.py`
- multi-symbol preflight integration test
- reconciliation pending-order detection integration test

### Manual verification

- operator-facing docs와 README가 동일한 설정 제약을 설명하는지 확인
- multi-symbol preflight 요청/응답 예시가 문서와 실제 contract에 맞는지 확인
- YAML 설정과 env-var override precedence가 운영자 관점에서 이해 가능한지 확인

## Recommended PR Slices

1. Phase 6 backlog/doc alignment
2. Multi-symbol preflight contract + tests
3. Pending-order source hardening + reconciliation tests
4. Configuration parity (`reconciliation_interval`, `portfolio_risk`) + config/docs/tests
5. Final doc sync + broader regression

## Risks and Fallbacks

- multi-symbol preflight DTO가 복잡해지면 기존 단일 readiness 소비자와의 호환성 비용이 커질 수 있다.
- KIS가 authoritative unresolved-order source를 충분히 제공하지 않으면 fallback 휴리스틱을 완전히 제거하지 못할 수 있다.
- config parity 작업은 `app.settings`와 `config.settings`의 해석 차이를 드러낼 수 있다.
- historical 문서 정리는 상태를 명확히 하지만, 구현 검증을 대체하지는 않는다.

대응:
- Step 1에서 backward compatibility contract를 먼저 고정한다.
- Step 2에서는 stronger source가 확인되기 전까지 fail-closed 규칙을 유지한다.
- Step 3에서는 YAML 지원 항목을 loader/tests/docs와 함께 한 slice에서 닫는다.
- Step 4에서는 task execution log와 residual risk를 실제 검증 결과로 채운다.
