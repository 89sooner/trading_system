# Phase 6 PRD

관련 문서:
- 이전 phase 범위/결과: `prd/phase_5_prd.md`
- 상세 구현 계획: `prd/phase_6_implementation_plan.md`
- 실행 및 검증 기록: `prd/phase_5_task.md`
- 실행 추적 기록: `prd/phase_6_task.md`
- 관련 히스토리: `prd/phase_4_task.md`, `prd/phase_3_task.md`

## 문서 목적

이 문서는 Phase 5 종료 시점에 남은 잔여 리스크 4개를 backlog로 승격하고, 이전 phase task 문서의 오래된 미체크 항목을 현재 기준에 맞게 정리하기 위해 정의된 `Phase 6` 기록이다.

Phase 6의 초점은 기능을 넓히는 것이 아니라, 이미 문서화된 운영 공백을 다음 구현 사이클의 공식 범위로 재정의하고, 과거 task 문서가 현재 진행 상태를 오해하게 만들지 않도록 기준선을 정리하는 데 있다.

## Goal

Phase 6의 목표는 국내주식 live 운영 경로의 잔여 불확실성을 줄이고, 설정/문서 기준선을 현재 시스템 상태와 일치시키는 것이다.

이번 phase는 다음 두 가지를 함께 달성해야 한다.

- Phase 5의 follow-up을 더 이상 참고 메모로 두지 않고, 구현 대상 backlog로 명시한다.
- Phase 3/4 task 문서의 오래된 미체크 항목을 "현재 PRD의 활성 미완료"와 구분되도록 정리한다.

## Current Baseline

- `prd/phase_5_task.md` 기준 Phase 5의 slice 5-0부터 5-6까지는 모두 완료되었다.
- `README.md`의 현재 로드맵 항목은 대시보드, 고급 리스크/애널리틱스, 멀티 심볼, 거래소 잔고 대사를 모두 delivered로 표시한다.
- 다만 Phase 5 execution log에는 다음 4개가 후속 리스크로 남아 있다.
  - `/api/v1/live/preflight`는 multi-symbol 요청에서 첫 심볼만 처리한다.
  - KIS pending order detection은 `hldg_qty != ord_psbl_qty` 휴리스틱에 의존한다.
  - reconciliation interval은 env-var로만 설정 가능하고 YAML loader parity가 없다.
  - `portfolio_risk`는 runtime/API 경로에서는 지원되지만 YAML loader에는 아직 연결되지 않았다.
- `prd/phase_3_task.md`, `prd/phase_4_task.md`에는 일부 unchecked 항목이 남아 있지만, 그중 상당수는 이후 phase에서 대체되었거나 수동 검증 성격의 히스토리 항목이다.

## Non-Goals

- 새로운 자산군(해외주식, 선물옵션, 암호화폐) 확장
- 신규 브로커 추가
- 실시간 스트리밍/WebSocket/SSE 인프라 도입
- 대시보드 대규모 재설계 또는 신규 route 추가
- 주문 정정/취소 workflow 전체 구현
- 장기 미체결 주문을 위한 완전한 비동기 order-state machine 도입
- 과거 phase task 문서를 삭제하거나 히스토리를 제거하는 정리 방식

## Hard Decisions

### D-1. Phase 6 backlog는 Phase 5의 잔여 리스크 4개에 한정한다

- 이번 문서에서 backlog로 승격하는 구현 항목은 정확히 아래 4개다.
  1. live preflight multi-symbol parity
  2. KIS pending order detection source hardening
  3. reconciliation interval YAML parity
  4. `portfolio_risk` YAML loader integration
- 그 외 항목은 새 근거가 생기기 전까지는 본 phase 범위에 자동 포함하지 않는다.

### D-2. 과거 task 문서 정리는 "삭제"가 아니라 "상태 명확화"로 처리한다

- `phase_3_task.md`, `phase_4_task.md`, `phase_5_task.md`의 기존 체크리스트는 히스토리로 유지한다.
- 다만 문서 상단 또는 관련 섹션에 상태 주석을 추가해, 현재 활성 backlog와 historical/manual-pending 항목을 구분한다.
- 과거 phase의 unchecked 항목을 현재 PRD blocker처럼 읽히게 두지 않는다.

### D-3. 설정 항목을 YAML에 노출하면 loader/tests/docs parity를 같이 맞춘다

- `TRADING_SYSTEM_RECONCILIATION_INTERVAL` 또는 `portfolio_risk`를 YAML에 승격하는 경우, `src/trading_system/config/settings.py`, `configs/`, `examples/`, `README.md`, 관련 테스트를 같은 phase 범위로 묶어야 한다.
- runtime/API-only 지원 상태를 유지한다면 문서에 그 제한을 명시적으로 남겨야 한다.

### D-4. 기존 operator/API surface를 우선 확장한다

- multi-symbol preflight를 다룰 때도 가능한 한 기존 `/api/v1/live/preflight` 경로를 유지한다.
- 신규 backlog는 기존 execution path와 operator surface를 기준으로 해결한다.

## Product Requirements

### PR-1. Live preflight의 multi-symbol parity 복구

- `/api/v1/live/preflight`는 현재 시스템의 multi-symbol orchestration 능력과 충돌하지 않는 형태로 확장되어야 한다.
- 다중 심볼 요청 시 첫 번째 심볼만 처리하는 현재 제한을 제거하거나, 제한을 유지한다면 API contract와 operator-facing docs에 명시적 제약으로 재정의해야 한다.
- readiness 결과는 심볼별 상태를 구분해 설명 가능해야 한다.

### PR-2. Pending order detection의 authoritative source 강화

- `pending_symbols` 생성은 가능한 한 전용 unresolved/open-order source를 기반으로 해야 한다.
- 현재 휴리스틱(`hldg_qty != ord_psbl_qty`) 의존은 축소 또는 제거되어야 한다.
- 전용 API 부재가 계속되면, fallback 조건과 fail-closed 규칙을 문서와 테스트에서 명시해야 한다.

### PR-3. Reconciliation 설정의 YAML parity 확보

- `TRADING_SYSTEM_RECONCILIATION_INTERVAL`은 env-var 전용 설정에서 벗어나 typed YAML loader 경로로도 설정 가능해야 한다.
- 설정 shape는 `configs/base.yaml`, 예제, README, 테스트와 함께 동기화되어야 한다.
- 운영자는 env-var 우선순위와 YAML 기본값의 관계를 문서만으로 이해할 수 있어야 한다.

### PR-4. `portfolio_risk` 설정 경로 일원화

- `portfolio_risk`는 API payload/AppSettings 경로뿐 아니라 `config.settings.load_settings()`에서도 파싱 가능해야 한다.
- YAML 예시는 참고용 주석이 아니라 실제 typed configuration path가 되어야 한다.
- loader가 지원하지 않는 필드를 운영 문서가 활성 기능처럼 안내하는 상태를 해소해야 한다.

### PR-5. Historical task 문서 상태 명확화

- `phase_3_task.md`, `phase_4_task.md`, `phase_5_task.md`는 현재 상태를 오해하지 않도록 status note를 가져야 한다.
- historical/manual-pending/superseded 항목은 현재 활성 backlog와 분리되어 보여야 한다.
- 문서 정리는 구현 히스토리와 검증 증적을 보존하는 방식이어야 한다.

## Scope By Epic

### Epic A. Multi-symbol preflight parity

목표:
- live preflight의 심볼 처리 범위를 현재 멀티심볼 실행 모델과 정렬한다.

포함:
- multi-symbol 요청 처리 또는 명시적 contract 재정의
- 심볼별 readiness 표현
- 관련 API schema/test/doc 갱신

제외:
- 신규 preflight endpoint 추가

### Epic B. Pending order detection hardening

목표:
- `pending_symbols`의 source를 휴리스틱보다 더 명확한 브로커 기준으로 강화한다.

포함:
- unresolved/open-order source 재검토
- fallback/fail-closed 규칙 명확화
- reconciliation and adapter 테스트 보강

제외:
- full async order-state machine

### Epic C. Configuration parity recovery

목표:
- reconciliation interval과 `portfolio_risk`의 설정 경로를 YAML 기준선과 맞춘다.

포함:
- typed loader 확장
- config/example/README/test parity
- env-var/YAML precedence 문서화

제외:
- unrelated config schema redesign

### Epic D. Task document hygiene

목표:
- 과거 phase의 열린 체크박스가 현재 backlog로 오인되지 않도록 문서 상태를 정리한다.

포함:
- historical status note 추가
- active backlog와 historical/manual verification 분리
- Phase 5 follow-up의 Phase 6 승격 명시

제외:
- 기존 execution log 삭제
- 과거 phase 문서의 대규모 서술 개편

## Impacted Files

### Planning and task docs
- `prd/phase_6_prd.md`
- `prd/phase_5_task.md`
- `prd/phase_4_task.md`
- `prd/phase_3_task.md`

### Configuration and runtime (future implementation scope)
- `src/trading_system/config/settings.py`
- `src/trading_system/app/settings.py`
- `configs/base.yaml`
- `examples/`

### API and execution (future implementation scope)
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/schemas.py`
- `src/trading_system/execution/kis_adapter.py`
- `src/trading_system/execution/reconciliation.py`
- `src/trading_system/integrations/kis.py`

### Validation and docs
- `tests/unit/test_config_settings.py`
- `tests/unit/test_execution_adapters_and_broker.py`
- `tests/unit/test_reconciliation.py`
- `tests/integration/test_config_loader_integration.py`
- `README.md`

## Delivery Slices

### Slice 0. Backlog and status alignment

- Phase 5 follow-up 4개를 Phase 6 backlog로 승격한다.
- 이전 phase task 문서에 status note를 추가한다.

### Slice 1. Multi-symbol preflight contract

- API/schema/doc 기준으로 multi-symbol preflight 처리 방식을 고정한다.

### Slice 2. Pending order source hardening

- 휴리스틱 의존을 줄이는 source/fallback 규칙을 확정한다.

### Slice 3. Configuration parity

- reconciliation interval과 `portfolio_risk`의 YAML loader parity를 맞춘다.

### Slice 4. Final doc sync

- README/config/example/test 문서 기준선을 최종 정리한다.

## Success Metrics

- Phase 5 follow-up 4개가 더 이상 단순 리스크 메모가 아니라, 명시적 backlog 항목으로 추적될 것
- multi-symbol preflight 처리 범위가 API contract와 operator 문서에서 일치할 것
- `TRADING_SYSTEM_RECONCILIATION_INTERVAL`과 `portfolio_risk`의 설정 경로가 문서와 loader 동작에서 일치할 것
- historical task 문서를 읽어도 현재 활성 backlog와 과거 히스토리를 혼동하지 않을 것

## Risks and Follow-up

- KIS가 전용 unresolved-order source를 충분히 제공하지 않으면, 휴리스틱 fallback을 완전히 제거하지 못할 수 있다.
- multi-symbol preflight 표현이 복잡해지면 기존 단일 readiness 응답 소비자와의 호환성 검토가 필요할 수 있다.
- 설정 parity를 복구하는 과정에서 env-var 우선순위와 YAML 기본값 간의 정책 충돌이 드러날 수 있다.
- 과거 task 문서 정리는 상태를 명확하게 만들지만, 실제 코드 검증을 대체하지는 않는다.
