# Phase 15 PRD

관련 문서:
- 이전 phase 범위/결과: `prd/phase_14_prd.md`
- 이전 phase 실행 검증: `prd/phase_14_task.md`
- 아키텍처 개요: `docs/architecture/overview.ko.md`
- 워크스페이스 분석: `docs/architecture/workspace-analysis.ko.md`
- 사용자 유즈케이스: `docs/architecture/user-use-cases.ko.md`
- 상세 구현 계획: `prd/phase_15_implementation_plan.md`
- 실행 추적: `prd/phase_15_task.md`

## 문서 목적

Phase 14까지의 코드는 live session history, durable order audit, dispatcher status, retention preview/prune을 구현했다. `docs/architecture/*`도 이 상태를 반영하지만, 더 깊게 보면 다음 구현 공백은 "기록을 남기는 것"이 아니라 "운영 중 기록을 신뢰하고 재사용하는 것"이다.

현재 KIS reconciliation은 잔고 스냅샷의 `ord_psbl_qty < hldg_qty` 신호로 pending symbol을 추론한다. 이는 fail-closed 경계로는 유효하지만, 주문 감사 record와 broker order id가 생긴 현재 기준으로는 broker-side unresolved/open order authority가 부족하다. 또한 live order audit wiring은 구현되어 있으나, Phase 14 task에 live session owner 기준 integration evidence가 아직 남아 있다.

Phase 15는 live 운영 신뢰도를 높이는 보강 phase다. 목표는 KIS 미체결 주문 근거를 별도 contract로 승격하고, order audit export/search를 최소 운영 도구로 확장하며, CLI/YAML/API 사이의 전략 설정 parity를 정리하고, TestClient hang에 취약하지 않은 live audit 검증 경계를 만드는 것이다.

## Goal

1. KIS 또는 broker adapter가 미체결/open order snapshot을 제공할 수 있는 contract를 추가하고, reconciliation pending 판단의 근거를 잔고 휴리스틱보다 명시적인 source로 강화한다.
2. live session owner 기준 order audit 생성/조회가 통합 테스트 또는 route-service 경계 테스트로 검증되게 한다.
3. order audit을 운영자가 사건 조사에 사용할 수 있도록 시간 범위 필터와 CSV/JSONL export contract를 추가한다.
4. `strategy.profile_id`와 inline pattern strategy 설정을 YAML/CLI/API에서 일관되게 사용할 수 있도록 config parity를 정리한다.
5. architecture docs와 runbook을 새 broker pending-order authority, audit export, config parity 기준으로 갱신한다.

이번 phase는 다음 원칙을 따른다.

- trading decision, sizing, risk rule semantics는 변경하지 않는다.
- 불확실한 broker 상태에서는 기존처럼 fail-closed 한다.
- broker별 미체결 주문 API가 없을 때도 잔고 기반 fallback은 명시적으로 남긴다.
- 감사 export는 운영 보조 기능이며, 외부 warehouse나 BI 파이프라인을 도입하지 않는다.
- config shape 변경은 `configs/`, `examples/`, `README.md`, architecture docs를 함께 갱신한다.

## Current Baseline

- `OrderAuditRecord`는 file/Supabase repository와 `/api/v1/order-audit` 조회 API를 갖는다.
- `LiveTradingLoop.audit_owner_id`는 live session id를 audit owner로 전달한다.
- Phase 14 task에는 live session owner 기준 order audit integration test가 미완료로 남아 있다.
- `KisApiClient.inquire_balance()`는 cash, positions, average costs, `pending_symbols`를 반환하지만, pending source는 `ord_psbl_qty` 기반 휴리스틱이다.
- `KisOrderResult.order_id`는 존재하지만 `FillEvent`에는 broker order id가 없어 step-level fill audit payload가 broker id를 안정적으로 보존하지 못한다.
- `app.settings.AppSettings`는 `strategy.profile_id`와 inline strategy 설정을 표현할 수 있지만, CLI parser는 strategy profile 선택 플래그를 제공하지 않는다.
- `config.settings.load_settings()`의 typed YAML loader는 runtime strategy 설정을 아직 1급 필드로 파싱하지 않는다.
- `/api/v1/order-audit`는 `scope`, `owner_id`, `symbol`, `event`, `limit` 필터만 제공하며 시간 범위, 정렬 방향, export format은 없다.
- `docs/architecture/workspace-analysis.ko.md`의 권장 다음 백로그는 외부 queue, session export, unresolved/open-order source, config parity, operational hardening을 남은 갭으로 둔다.

## Non-Goals

- Redis/Celery/Kafka 같은 외부 queue 또는 분산 worker 도입
- 완전한 OMS, cancel/replace, bracket order, order status polling daemon 구현
- KIS 외 다른 broker의 실제 미체결 주문 API 연동
- 다중 사용자 RBAC, SSO, tenant 분리
- 감사 데이터를 외부 warehouse로 적재하는 managed export pipeline
- 전략 승인/promotion workflow
- 백테스트 성능 최적화 또는 analytics 지표 확장

## Hard Decisions

### D-1. Pending order authority는 broker capability로 추가한다

`AccountBalanceSnapshot.pending_symbols`는 유지하되, 새 `OpenOrderSnapshot` 또는 동등한 DTO를 broker capability로 추가한다. reconciliation은 open-order snapshot을 우선 사용하고, broker가 제공하지 못하거나 조회 실패하면 기존 balance snapshot의 pending signal을 fallback으로 사용한다. 조회 실패는 포트폴리오를 수정하지 않는 fail-closed 경계로 처리한다.

### D-2. Broker order id는 fill event의 optional metadata로 승격한다

`KisOrderResult.order_id`가 audit record까지 도달하려면 `FillEvent` 또는 execution event payload에 optional `broker_order_id`가 필요하다. 필드는 optional로 두어 simulator와 기존 테스트를 깨지 않으며, KIS adapter만 값을 채운다.

### D-3. Audit export는 API-level streaming이 아니라 bounded response로 시작한다

초기 export는 `limit <= 5000` 같은 상한을 둔 CSV/JSONL response로 제한한다. 대량 감사 로그를 위한 object storage, background export job, signed URL은 이번 phase 범위에서 제외한다.

### D-4. Config parity는 typed YAML을 runtime settings로 변환하는 단일 helper로 맞춘다

`config.settings`와 `app.settings`를 무리하게 합치지 않는다. 대신 YAML loader가 strategy section을 typed하게 파싱하고, CLI/API가 쓰는 `AppSettings`로 변환하는 작은 adapter를 둔다. CLI에는 `--strategy-profile-id`와 최소 inline pattern strategy 옵션을 추가하되, 복잡한 JSON 입력은 config file 경로를 권장한다.

### D-5. TestClient hang을 우회하는 검증 경계를 공식화한다

Phase 13/14에서 `TestClient(create_app())` lifespan hang이 반복되었다. Phase 15의 live audit 검증은 route handler + repository + live loop service boundary를 직접 조합하는 테스트를 우선 작성하고, TestClient 기반 통합 테스트는 별도 smoke로 유지한다.

## Product Requirements

### PR-1. Broker open-order authority

- broker adapter contract는 open/unresolved order snapshot을 optional로 제공할 수 있어야 한다.
- snapshot은 최소 `broker_order_id`, `symbol`, `side`, `requested_quantity`, `remaining_quantity`, `status`, `submitted_at`을 표현해야 한다.
- KIS adapter는 가능한 KIS 응답을 통해 open order snapshot을 구성해야 한다.
- KIS open-order 조회 실패 또는 필수 필드 누락 시 reconciliation은 포트폴리오를 조정하지 않고 skip/fail-closed 이벤트를 남겨야 한다.
- open-order snapshot이 제공되면 pending symbols는 이 snapshot을 우선 기준으로 계산해야 한다.

### PR-2. Broker order id audit propagation

- KIS order submission 결과의 `order_id`가 fill event 또는 audit payload로 보존되어야 한다.
- `/api/v1/order-audit` 응답의 `broker_order_id`는 KIS 주문 감사 record에서 채워져야 한다.
- simulator와 기존 backtest path는 broker order id가 없어도 동일하게 동작해야 한다.

### PR-3. Live session audit verification

- live paper 또는 stubbed live loop 실행에서 `scope=live_session`, `owner_id=session_id` audit record가 생성되는 테스트가 있어야 한다.
- 테스트는 `TestClient(create_app())` lifespan에 의존하지 않아야 한다.
- audit repository append 실패가 live loop tick 상태와 portfolio persistence를 깨지 않는 regression test가 있어야 한다.

### PR-4. Order audit search and export

- audit list API는 `start`, `end`, `status`, `side`, `broker_order_id`, `sort` 필터를 지원해야 한다.
- export API는 owner/scope/time filter를 적용한 CSV와 JSONL 중 하나를 요청할 수 있어야 한다.
- export 응답은 record count와 applied filter를 알 수 있어야 한다.
- frontend는 run detail 또는 dashboard session detail에서 owner 기준 audit export action을 제공해야 한다.

### PR-5. Strategy config parity

- typed YAML config는 `strategy.profile_id` 또는 inline pattern strategy section을 파싱할 수 있어야 한다.
- YAML config에서 읽은 strategy 설정은 `AppSettings.strategy`와 같은 validation semantics를 사용해야 한다.
- CLI는 저장된 strategy profile을 선택하는 플래그를 제공해야 한다.
- `configs/base.yaml`, `examples/*.yaml`, `README.md`는 새 설정 shape와 우선순위를 설명해야 한다.

## Scope By Epic

### Epic A. Broker open-order and reconciliation authority

목표:
- reconciliation pending 판단을 broker-side open order source로 강화한다.

포함:
- open order DTO/protocol
- `BrokerSimulator` optional capability
- KIS open/unresolved order 조회 구현
- reconciliation 우선순위 변경
- KIS parser/fail-closed 테스트

제외:
- 주문 취소/정정 실행
- long-running order polling worker
- KIS 외 broker의 실제 open order API

### Epic B. Audit propagation, search, and export

목표:
- order audit이 live 사건 조사와 운영 리포팅에 바로 쓸 수 있는 최소 표면을 갖게 한다.

포함:
- broker order id propagation
- audit repository 필터 확장
- CSV/JSONL export API
- run/session owner 기준 frontend export action
- live session owner audit regression test

제외:
- 대량 비동기 export job
- 외부 object storage upload
- full-text search

### Epic C. Strategy configuration parity

목표:
- CLI, YAML, API에서 strategy profile/inline strategy 설정 의미가 갈라지지 않게 한다.

포함:
- YAML strategy section parser
- YAML-to-`AppSettings` adapter
- CLI strategy profile flag
- config/examples/README 업데이트
- validation regression test

제외:
- 전략 approval/promotion workflow
- plugin registry
- UI strategy editor 확장

### Epic D. Docs and verification baseline

목표:
- 반복된 TestClient hang 리스크와 새 운영 contract를 문서와 테스트 기준에 반영한다.

포함:
- route-service boundary integration test pattern 문서화
- architecture docs 업데이트
- KIS/live runbook 업데이트
- release gate checklist 업데이트

제외:
- 전체 테스트 인프라 교체
- CI provider 변경

## Impacted Files

### Broker and reconciliation
- `src/trading_system/execution/broker.py`
- `src/trading_system/execution/kis_adapter.py`
- `src/trading_system/execution/reconciliation.py`
- `src/trading_system/integrations/kis.py`
- `src/trading_system/app/loop.py`

### Order audit API, repository, and frontend
- `src/trading_system/execution/order_audit.py`
- `src/trading_system/api/routes/order_audit.py`
- `src/trading_system/api/schemas.py`
- `src/trading_system/api/server.py`
- `frontend/lib/api/types.ts`
- `frontend/lib/api/backtests.ts`
- `frontend/lib/api/dashboard.ts`
- `frontend/app/runs/[runId]/page.tsx`
- `frontend/components/dashboard/SessionDetailDialog.tsx`

### Configuration and CLI
- `src/trading_system/config/settings.py`
- `src/trading_system/app/settings.py`
- `src/trading_system/app/main.py`
- `src/trading_system/app/services.py`
- `configs/base.yaml`
- `examples/sample_backtest.yaml`
- `examples/sample_backtest_krx.yaml`
- `examples/sample_live_kis.yaml`
- `README.md`

### Validation and docs
- `tests/unit/test_kis_integration.py`
- `tests/unit/test_kis_reconciliation_integration.py`
- `tests/unit/test_reconciliation.py`
- `tests/unit/test_order_audit_repository.py`
- `tests/unit/test_order_audit_routes.py`
- `tests/unit/test_live_loop.py`
- `tests/unit/test_config_settings.py`
- `tests/unit/test_app_main.py`
- `tests/integration/test_order_audit_integration.py`
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

## Delivery Slices

### Slice 0. Open-order contract and KIS parser
- broker open-order DTO/protocol과 KIS 응답 parser를 추가한다.

### Slice 1. Reconciliation pending authority hardening
- reconciliation이 open-order snapshot을 우선 사용하고 fallback/fail-closed 이벤트를 명확히 남기게 한다.

### Slice 2. Broker order id audit propagation and live audit verification
- KIS order id를 audit record까지 전달하고 live session owner 기준 regression test를 추가한다.

### Slice 3. Order audit filter/export
- audit repository/API/frontend에 시간 범위, 상태, broker id 필터와 CSV/JSONL export를 추가한다.

### Slice 4. Strategy config parity
- YAML/CLI/API strategy 설정 의미를 정렬하고 config/examples/README를 갱신한다.

### Slice 5. Docs and verification alignment
- architecture docs, KIS runbook, incident response, release gate checklist를 새 contract에 맞춘다.

## Success Metrics

- KIS open-order snapshot parser가 정상/누락/오류 응답을 테스트로 검증한다.
- reconciliation은 open-order snapshot이 있을 때 해당 source로 pending symbols를 계산하고, 조회 실패 시 포트폴리오를 수정하지 않는다.
- KIS order id가 `broker_order_id`로 order audit record에 보존된다.
- live session owner 기준 order audit 생성 테스트가 TestClient lifespan 없이 통과한다.
- `/api/v1/order-audit`는 시간 범위/status/side/broker_order_id 필터와 bounded CSV/JSONL export를 제공한다.
- YAML config와 CLI가 저장된 strategy profile을 선택할 수 있고, validation 오류가 API runtime 설정과 일관된다.
- `docs/architecture/*`와 runbook이 pending-order authority, audit export, config parity 상태를 실제 코드와 충돌 없이 설명한다.

## Risks and Follow-up

- KIS open-order API 응답 shape가 운영 계좌/모의 계좌에서 다를 수 있다. parser는 fixture 기반으로 보수적으로 시작하고, 불확실하면 fail-closed 해야 한다.
- broker order id를 `FillEvent`에 추가하면 테스트 fixture 수정 범위가 넓어질 수 있다. optional field와 default 값으로 blast radius를 제한한다.
- CSV/JSONL export는 개인정보나 계좌 정보를 포함할 수 있으므로 API key 보호와 필터 상한을 유지해야 한다.
- YAML strategy parity는 설정 shape 변경이므로 `configs/`, `examples/`, `README.md`를 같은 변경에 포함해야 한다.
- 외부 queue/분산 worker는 여전히 후속 대형 phase로 남는다.
