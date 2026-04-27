# Phase 14 PRD

관련 문서:
- 이전 phase 범위/결과: `prd/phase_13_prd.md`
- 이전 phase 실행 검증: `prd/phase_13_task.md`
- 아키텍처 개요: `docs/architecture/overview.ko.md`
- 워크스페이스 분석: `docs/architecture/workspace-analysis.ko.md`
- 사용자 유즈케이스: `docs/architecture/user-use-cases.ko.md`
- 상세 구현 계획: `prd/phase_14_implementation_plan.md`
- 실행 추적: `prd/phase_14_task.md`

## 문서 목적

Phase 13까지의 구현으로 백테스트 run metadata, live runtime session history, API key governance, 운영 콘솔이 기본적으로 연결되었다. 코드를 다시 보면 백테스트 실행은 이미 `BacktestRunDispatcher`와 `queued/running/succeeded/failed` 상태를 통해 요청 경로에서 분리되었고, live session history도 파일 또는 Supabase 저장소에 남는다. 따라서 다음 구현 공백은 단순히 "비동기 실행 모델 추가"가 아니라, 이미 생긴 운영 기록을 운영자가 신뢰할 수 있는 표면으로 만들고 주문 단위 감사 가능성을 보강하는 것이다.

`docs/architecture/*`는 아직 과거 세션 탐색 UX, 주문 lifecycle 저장소 부재, run 보존 정책 부재, queue 운영 가시성 부족을 주요 갭으로 남기고 있다. Phase 14는 이 갭을 하나의 운영 관점으로 묶는다. 목표는 live session history를 브라우저에서 탐색 가능하게 만들고, 백테스트/라이브 주문 이벤트를 durable audit record로 남기며, run/session/order 기록에 대한 보존과 운영 가시성을 최소 제품 수준으로 끌어올리는 것이다.

## Goal

1. 운영자가 프론트엔드에서 과거 live runtime session을 조회하고, preflight/종료 상태/오류를 빠르게 확인할 수 있게 한다.
2. `execute_trading_step`에서 발생하는 주문 생성/체결/거절 이벤트를 백테스트와 라이브가 공유하는 durable order audit contract로 저장할 수 있게 한다.
3. backtest run queue와 저장소 보존(retention)에 대한 API와 운영자 UI를 추가해 장시간/누적 실행의 운영 부담을 낮춘다.
4. `docs/architecture/*`와 runbook을 새 운영 기록 모델에 맞춰 다시 정렬한다.

이번 phase는 다음 원칙을 따른다.

- trading semantics, 주문 수량 계산, 리스크 판정 결과는 바꾸지 않는다.
- 기존 event log를 대체하지 않고, 감사와 조회에 필요한 최소 order record만 별도로 추가한다.
- file repository와 Supabase repository가 같은 contract를 구현해야 한다.
- UI는 운영자가 실제로 탐색해야 하는 정보만 먼저 노출하고, 대형 리포팅/검색 플랫폼은 도입하지 않는다.

## Current Baseline

- `BacktestRunDispatcher`는 queued/running/final 상태를 저장하지만, queue depth, worker 상태, 보존 정책, 운영자용 정리 API는 없다.
- `LiveRuntimeSessionRecord`는 durable하게 저장되고 API로 조회되지만, 프론트엔드에는 과거 세션 전용 탐색 화면이 없다.
- `execute_trading_step`은 `order.created`, `order.filled`, `order.rejected`, `risk.rejected` 이벤트를 emit하지만, 주문 단위 durable store는 없다.
- KIS 실주문 경로는 `KisBrokerAdapter`를 통해 fill event로 정규화되지만, broker order id나 주문 lifecycle 감사 record를 보존하는 contract가 없다.
- `FileBacktestRunRepository`와 `SupabaseBacktestRunRepository`는 delete/clear를 지원하지만, retention dry-run, cutoff 기반 pruning, admin API는 없다.
- 프론트엔드 `dashboard`는 active runtime 모니터링에 강하지만, 종료된 session과 과거 order audit을 탐색하지 못한다.
- `docs/architecture/workspace-analysis.ko.md`는 백테스트 실행이 동기 실행이라고 설명하는 부분이 남아 있어 현재 코드와 맞지 않는다.

## Non-Goals

- 외부 queue 서비스, Celery, Redis, Kafka 같은 신규 인프라 도입
- 완전한 OMS(order management system) 구현
- broker별 미체결 주문 취소/정정 워크플로
- 다중 사용자 RBAC, SSO, 고객별 테넌트 분리
- full-text audit search 또는 대규모 리포팅 warehouse
- 전략 promotion/approval workflow
- 주문 체결 알고리즘 또는 리스크 정책 변경

## Hard Decisions

### D-1. Session history UX는 dashboard 안의 운영 패널로 시작한다

별도 대형 운영 앱을 만들지 않고 `frontend/app/dashboard/page.tsx` 안에 최근 세션 패널과 상세 dialog를 추가한다. 현재 dashboard가 active runtime의 진실 원천이므로, 과거 session 진입점도 같은 운영 콘솔에 두는 것이 사용자의 mental model과 맞다.

### D-2. Order audit은 trading step 이벤트에서 파생하되 별도 저장소에 보존한다

기존 structured logger는 실시간 이벤트 전달과 화면 표시에 적합하지만, 주문 감사에는 조회 가능한 안정 contract가 필요하다. 따라서 `OrderAuditRecord`를 새로 정의하고, `execute_trading_step` 또는 그 호출 경계에서 order/risk 이벤트를 append한다. 기존 이벤트 payload는 유지하되, audit record에는 `scope`, `run_id/session_id`, `symbol`, `side`, `quantity`, `status`, `reason`, `timestamp`, `broker_order_id` 같은 조회 필드를 1급화한다.

### D-3. Retention은 삭제 실행과 dry-run을 분리한다

운영 기록 삭제는 되돌리기 어렵다. cutoff 기반 retention API는 먼저 삭제 대상과 개수를 preview할 수 있어야 하며, 실제 prune은 명시적인 confirm payload를 요구한다.

### D-4. Supabase schema 변화는 additive migration으로만 수행한다

Phase 14는 운영 기록을 추가하는 단계이므로 기존 `backtest_runs`, `live_runtime_sessions`, API key schema를 깨지 않는다. 새 order audit table과 선택적 index를 additive하게 추가하고, 파일 저장소도 같은 shape로 직렬화한다.

## Product Requirements

### PR-1. Live session history browser workflow

- dashboard에서 최근 live runtime session 목록을 조회할 수 있어야 한다.
- 각 session은 `session_id`, 시작/종료 시각, provider, broker, live execution, symbols, final state, last error를 표시해야 한다.
- session detail은 preflight summary와 warning/blocking reason을 보여줘야 한다.
- API 호출 실패, 빈 목록, loading 상태가 모두 UI에서 명확히 처리되어야 한다.

### PR-2. Durable order audit record

- 백테스트와 라이브 실행에서 발생한 주문 생성/체결/거절/리스크 거절을 durable record로 저장할 수 있어야 한다.
- record는 최소한 `record_id`, `scope`, `owner_id`, `event`, `symbol`, `side`, `requested_quantity`, `filled_quantity`, `price`, `status`, `reason`, `timestamp`, `payload`를 포함해야 한다.
- list API는 `scope`, `owner_id`, `symbol`, `event`, `limit` 필터를 지원해야 한다.
- 백테스트 run detail과 live session detail에서 해당 owner의 order audit을 조회할 수 있어야 한다.

### PR-3. Backtest run queue and retention visibility

- API는 dispatcher worker 상태와 현재 queue depth를 반환해야 한다.
- run list UI는 queued/running 상태를 운영자가 이해할 수 있게 표시하고, 필요 시 polling cadence를 유지해야 한다.
- retention preview API는 cutoff/status 기준 삭제 대상 개수를 반환해야 한다.
- retention prune API는 명시 confirm 값이 있을 때만 삭제를 수행해야 한다.

### PR-4. Documentation alignment

- `docs/architecture/workspace-analysis.ko.md`와 영문본은 현재 async dispatcher 상태를 반영해야 한다.
- user use case 문서는 session history UX, order audit, retention workflow를 새 진입점으로 설명해야 한다.
- 운영 runbook은 retention/prune과 order audit 조회 절차를 포함해야 한다.

## Scope By Epic

### Epic A. Session history UX

목표:
- 이미 저장되는 live runtime session history를 운영자가 브라우저에서 탐색하게 만든다.

포함:
- frontend API 타입/client 추가
- dashboard session history panel
- session detail dialog
- loading/empty/error 상태
- e2e 또는 component-level smoke 검증

제외:
- 고급 검색, CSV export, incident timeline full drill-down

### Epic B. Order audit persistence

목표:
- 주문 lifecycle과 리스크 거절을 run/session owner 기준으로 durable하게 조회하게 만든다.

포함:
- order audit DTO/protocol/repository
- file/Supabase 저장소
- trading step 호출 경계에서 audit append
- list/detail API
- 백테스트 run/live session detail 연결

제외:
- 주문 취소/정정 명령
- broker별 order status polling
- 외부 감사 export

### Epic C. Queue visibility, retention, docs

목표:
- 운영자가 run queue와 저장소 누적 상태를 이해하고, 오래된 기록을 안전하게 정리할 수 있게 한다.

포함:
- dispatcher status API
- retention preview/prune service
- admin 또는 runs UI의 최소 retention control
- architecture docs/runbook 업데이트

제외:
- cron scheduler
- 자동 삭제 기본 활성화
- multi-tenant quota

## Impacted Files

### Runtime/session frontend
- `frontend/lib/api/types.ts`
- `frontend/lib/api/dashboard.ts`
- `frontend/app/dashboard/page.tsx`
- 신규 `frontend/components/dashboard/SessionHistoryPanel.tsx`
- 신규 `frontend/components/dashboard/SessionDetailDialog.tsx`
- `frontend/e2e/smoke.spec.ts`

### Order audit domain and repositories
- 신규 `src/trading_system/execution/order_audit.py`
- `src/trading_system/execution/step.py`
- `src/trading_system/backtest/engine.py`
- `src/trading_system/app/loop.py`
- `src/trading_system/app/services.py`
- `src/trading_system/api/server.py`
- 신규 `src/trading_system/api/routes/order_audit.py`
- `src/trading_system/api/schemas.py`
- 신규 `scripts/migrations/004_add_order_audit_records.sql`

### Queue, retention, and admin surfaces
- `src/trading_system/backtest/dispatcher.py`
- `src/trading_system/backtest/repository.py`
- `src/trading_system/backtest/file_repository.py`
- `src/trading_system/backtest/supabase_repository.py`
- `src/trading_system/api/routes/backtest.py`
- `frontend/app/runs/page.tsx`
- `frontend/lib/api/backtests.ts`

### Validation and docs
- `tests/unit/test_backtest_dispatcher.py`
- 신규 `tests/unit/test_order_audit_repository.py`
- 신규 `tests/unit/test_order_audit_routes.py`
- `tests/unit/test_backtest_engine.py`
- `tests/unit/test_live_loop.py`
- `tests/integration/test_backtest_run_api_integration.py`
- `tests/integration/test_live_runtime_api_integration.py`
- 신규 `tests/integration/test_order_audit_integration.py`
- `docs/architecture/overview.ko.md`
- `docs/architecture/overview.md`
- `docs/architecture/workspace-analysis.ko.md`
- `docs/architecture/workspace-analysis.md`
- `docs/architecture/user-use-cases.ko.md`
- `docs/architecture/user-use-cases.md`
- `docs/runbooks/deploy-production.ko.md`
- `docs/runbooks/deploy-production.md`

## Delivery Slices

### Slice 0. Live session history UX
- dashboard에서 최근 session 목록과 detail dialog를 제공한다.

### Slice 1. Order audit contract and repository
- order audit DTO/protocol/file/Supabase repository와 migration을 추가한다.

### Slice 2. Backtest/live order audit wiring and API
- 백테스트와 라이브 실행 경계에서 audit record를 저장하고 조회 API를 추가한다.

### Slice 3. Queue/retention operations
- dispatcher status, retention preview/prune, UI 최소 제어를 구현한다.

### Slice 4. Docs and runbook alignment
- architecture docs와 운영 runbook을 새 session history/order audit/retention contract에 맞춰 정렬한다.

## Success Metrics

- dashboard에서 최근 live session 목록과 preflight/오류 상세를 확인할 수 있다.
- 백테스트 run 또는 live session owner id로 주문 감사 record를 조회할 수 있다.
- file 저장소와 Supabase 저장소 모두 order audit record 저장/조회 테스트를 통과한다.
- dispatcher status API가 worker running 여부와 queue depth를 반환한다.
- retention preview/prune은 dry-run과 confirm 실행이 분리되어 있다.
- `docs/architecture/*`가 async dispatcher, session history UX, order audit, retention 상태를 실제 코드와 충돌 없이 설명한다.

## Risks and Follow-up

- order audit wiring이 trading step에 직접 결합되면 백테스트 결정성을 해칠 수 있으므로, 저장 실패는 기본적으로 trading result를 바꾸지 않는 best-effort 경계에서 처리해야 한다.
- KIS broker order id가 현재 adapter contract에 없으므로 초기 phase에서는 optional field로 두고, KIS client가 제공하는 값만 채운다.
- retention prune은 운영 데이터 삭제 위험이 있으므로 API key 보호와 confirm payload를 필수로 둔다.
- session history UI가 커질 경우 별도 `/sessions` 라우트로 분리할 수 있지만, 초기에는 dashboard 내 패널로 제한한다.
