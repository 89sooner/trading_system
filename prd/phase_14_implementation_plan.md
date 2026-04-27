# Phase 14 Implementation Plan

## Goal

Phase 14의 구현 목표는 Phase 13까지 추가된 운영 기록을 실제 운영 워크플로로 완성하는 것이다. live session history는 브라우저에서 탐색 가능하게 만들고, 주문 lifecycle은 durable audit record로 남기며, backtest queue와 retention 상태는 API/UI에서 운영자가 확인하고 제어할 수 있게 한다.

핵심 구현 원칙:

1. trading semantics와 리스크 판정은 변경하지 않는다.
2. 감사 저장 실패가 백테스트/라이브 실행 결과를 바꾸지 않게 한다.
3. file/Supabase 저장소 contract를 함께 구현한다.
4. 삭제성 작업은 preview와 confirm 실행을 분리한다.
5. 문서는 구현 범위의 일부로 업데이트한다.

## Preconditions

- `BacktestRunDispatcher`는 현재 baseline으로 유지하며, 외부 queue 인프라는 도입하지 않는다.
- `LiveRuntimeSessionRecord`와 `/api/v1/live/runtime/sessions`는 이미 존재하므로, backend session API는 확장보다 frontend 소비가 중심이다.
- 주문 감사 record는 기존 structured event payload에서 파생하며, `execute_trading_step`의 반환 결과와 포트폴리오 mutation 순서는 바꾸지 않는다.
- Supabase 변경은 additive migration으로만 수행한다.
- retention prune은 기본 비활성 동작이며, 명시 confirm이 없으면 삭제하지 않는다.

## Locked Design Decisions

### 1. Session history는 dashboard 패널로 구현한다

- `frontend/app/dashboard/page.tsx`에 session history 패널을 추가한다.
- 세션 상세는 페이지 전환이 아니라 dialog로 제공한다.
- 초기 필터는 limit 기반 최근 목록으로 제한한다.

### 2. Order audit 저장은 owner scope 기반으로 설계한다

- `scope`는 `backtest` 또는 `live_session`으로 고정한다.
- `owner_id`는 backtest `run_id` 또는 live `session_id`를 의미한다.
- 조회 API는 `/api/v1/order-audit` 계열로 두고, frontend는 run/session 화면에서 owner 기준으로 호출한다.

### 3. Audit append는 best-effort boundary에서 처리한다

- 저장소 장애가 주문 실행 결과를 바꾸면 안 된다.
- audit repository가 없거나 저장에 실패하면 structured logger에 warning을 남기고 trading step은 계속 진행한다.

### 4. Retention은 repository protocol의 선택적 확장으로 구현한다

- 기존 `delete`, `clear`는 유지한다.
- cutoff/status 기반 preview/prune 메서드를 repository contract에 추가하거나 별도 retention service가 repository list/delete를 조합한다.
- Supabase는 SQL cutoff delete를 사용하고, file repo는 index를 기준으로 후보를 산정한다.

## Contract Deltas

## A. Live session frontend contract

대상:
- `frontend/lib/api/types.ts`
- `frontend/lib/api/dashboard.ts`
- `frontend/app/dashboard/page.tsx`
- 신규 `frontend/components/dashboard/SessionHistoryPanel.tsx`
- 신규 `frontend/components/dashboard/SessionDetailDialog.tsx`

필수 변화:
- `LiveRuntimeSessionRecord`와 `LiveRuntimeSessionList` 타입 추가
- `/live/runtime/sessions`와 `/live/runtime/sessions/{session_id}` client 함수 추가
- dashboard에서 최근 session 목록, final state, last error, preflight summary 표시

비고:
- backend DTO shape는 Phase 13 contract를 우선 재사용한다.

## B. Order audit persistence contract

대상:
- 신규 `src/trading_system/execution/order_audit.py`
- `src/trading_system/api/schemas.py`
- 신규 `src/trading_system/api/routes/order_audit.py`
- `src/trading_system/api/server.py`
- 신규 `scripts/migrations/004_add_order_audit_records.sql`

필수 변화:
- `OrderAuditRecord` DTO와 repository protocol 정의
- file/Supabase repository 구현
- list API에 `scope`, `owner_id`, `symbol`, `event`, `limit` 필터 추가
- Supabase migration과 index 추가

비고:
- record payload는 원본 event payload를 보존하되, 조회 필드는 별도 컬럼/필드로 승격한다.

## C. Trading runtime audit wiring

대상:
- `src/trading_system/execution/step.py`
- `src/trading_system/backtest/engine.py`
- `src/trading_system/app/loop.py`
- `src/trading_system/app/services.py`

필수 변화:
- `TradingContext` 또는 호출 경계에 audit sink 추가
- 백테스트 실행 시 `scope=backtest`, `owner_id=run_id`로 record 저장
- 라이브 실행 시 `scope=live_session`, `owner_id=session_id`로 record 저장
- risk rejection, order rejection, fill event를 audit record로 정규화

비고:
- backtest engine이 run_id를 모르던 경로는 optional owner id를 주입받도록 additive하게 확장한다.

## D. Queue and retention operations

대상:
- `src/trading_system/backtest/dispatcher.py`
- `src/trading_system/backtest/repository.py`
- `src/trading_system/backtest/file_repository.py`
- `src/trading_system/backtest/supabase_repository.py`
- `src/trading_system/api/routes/backtest.py`
- `frontend/app/runs/page.tsx`
- `frontend/lib/api/backtests.ts`

필수 변화:
- dispatcher status snapshot에 `running`, `queue_depth`, `max_queue_size` 추가
- `/api/v1/backtests/dispatcher` 또는 동등한 status endpoint 추가
- retention preview/prune endpoint 추가
- runs UI에 queue status와 retention preview/action 최소 표면 추가

비고:
- prune API는 `confirm="DELETE"` 또는 동등한 explicit confirmation을 요구한다.

## Sequenced Implementation

### Step 0. Live session history UX

목적:
- 저장된 live runtime session history를 운영자가 dashboard에서 탐색하게 한다.

파일:
- `frontend/lib/api/types.ts`
- `frontend/lib/api/dashboard.ts`
- `frontend/app/dashboard/page.tsx`
- 신규 `frontend/components/dashboard/SessionHistoryPanel.tsx`
- 신규 `frontend/components/dashboard/SessionDetailDialog.tsx`
- `frontend/e2e/smoke.spec.ts`

구체 작업:
- session list/detail 타입과 client 함수를 추가한다.
- React Query로 최근 session list를 dashboard에서 조회한다.
- session row에 state, duration, provider/broker, symbols, error badge를 표시한다.
- detail dialog에 preflight summary, warnings, blocking reasons, timestamps를 표시한다.
- 빈 목록, loading, API error 상태를 처리한다.

종료 조건:
- dashboard에서 최근 live session 목록을 볼 수 있고, 하나를 선택해 detail을 확인할 수 있다.

### Step 1. Order audit DTO/repository/migration 추가

목적:
- 주문 lifecycle 감사 record를 저장하고 조회하는 독립 contract를 만든다.

파일:
- 신규 `src/trading_system/execution/order_audit.py`
- `src/trading_system/api/schemas.py`
- 신규 `src/trading_system/api/routes/order_audit.py`
- `src/trading_system/api/server.py`
- 신규 `scripts/migrations/004_add_order_audit_records.sql`
- 신규 `tests/unit/test_order_audit_repository.py`
- 신규 `tests/unit/test_order_audit_routes.py`

구체 작업:
- `OrderAuditRecord`와 `OrderAuditRepository` protocol을 정의한다.
- file repository와 Supabase repository를 구현한다.
- `create_order_audit_repository()` factory를 추가한다.
- API DTO와 list endpoint를 추가한다.
- Supabase table/index migration을 작성한다.

종료 조건:
- file/Supabase mocked repository 테스트와 order audit route 테스트가 통과한다.

### Step 2. Backtest/live audit wiring

목적:
- 실제 백테스트와 라이브 실행에서 audit record가 owner 기준으로 남게 한다.

파일:
- `src/trading_system/execution/step.py`
- `src/trading_system/backtest/engine.py`
- `src/trading_system/app/loop.py`
- `src/trading_system/app/services.py`
- `src/trading_system/api/routes/backtest.py`
- `tests/unit/test_backtest_engine.py`
- `tests/unit/test_live_loop.py`
- 신규 `tests/integration/test_order_audit_integration.py`

구체 작업:
- audit sink interface를 `TradingContext` 또는 실행 호출 경계에 추가한다.
- order/risk event를 `OrderAuditRecord`로 변환하는 helper를 만든다.
- backtest create 경로가 run_id를 engine/services로 전달하게 한다.
- live runtime controller가 session_id를 live loop audit owner로 전달하게 한다.
- 저장 실패가 실행 결과를 바꾸지 않는지 regression test를 추가한다.

종료 조건:
- 백테스트 run과 live session owner id로 order audit record를 조회할 수 있다.

### Step 3. Queue status와 retention operations 추가

목적:
- 운영자가 queue 상태와 저장소 누적 기록을 보고 안전하게 정리할 수 있게 한다.

파일:
- `src/trading_system/backtest/dispatcher.py`
- `src/trading_system/backtest/repository.py`
- `src/trading_system/backtest/file_repository.py`
- `src/trading_system/backtest/supabase_repository.py`
- `src/trading_system/api/routes/backtest.py`
- `frontend/lib/api/backtests.ts`
- `frontend/app/runs/page.tsx`
- `tests/unit/test_backtest_dispatcher.py`
- `tests/unit/test_file_repository.py`
- `tests/unit/test_supabase_repository.py`
- `tests/integration/test_backtest_run_api_integration.py`

구체 작업:
- dispatcher snapshot 메서드와 API endpoint를 추가한다.
- retention preview service를 구현한다.
- retention prune endpoint는 explicit confirm 없이는 400을 반환하게 한다.
- runs 화면에 queue status와 retention preview/action 최소 UI를 추가한다.
- cutoff/status 필터별 preview/prune 테스트를 추가한다.

종료 조건:
- dispatcher 상태가 API/UI에 표시되고, retention preview/prune이 안전장치와 함께 동작한다.

### Step 4. Docs and runbook alignment

목적:
- architecture docs와 운영 runbook이 실제 구현 상태를 설명하게 한다.

파일:
- `docs/architecture/overview.ko.md`
- `docs/architecture/overview.md`
- `docs/architecture/workspace-analysis.ko.md`
- `docs/architecture/workspace-analysis.md`
- `docs/architecture/user-use-cases.ko.md`
- `docs/architecture/user-use-cases.md`
- `docs/runbooks/deploy-production.ko.md`
- `docs/runbooks/deploy-production.md`

구체 작업:
- 백테스트 async dispatcher 상태를 현재 코드 기준으로 정정한다.
- session history UX와 order audit API를 사용자 유즈케이스에 추가한다.
- retention preview/prune 운영 절차를 runbook에 추가한다.
- Supabase migration 적용 순서에 `004_add_order_audit_records.sql`을 추가한다.

종료 조건:
- docs가 Phase 14 구현 후 API/UI/storage contract와 충돌하지 않는다.

## Validation Matrix

### Required unit tests
- `pytest tests/unit/test_order_audit_repository.py -q`
- `pytest tests/unit/test_order_audit_routes.py -q`
- `pytest tests/unit/test_backtest_dispatcher.py -q`
- `pytest tests/unit/test_file_repository.py -q`
- `pytest tests/unit/test_supabase_repository.py -q`
- `pytest tests/unit/test_backtest_engine.py -q`
- `pytest tests/unit/test_live_loop.py -q`

### Required integration tests
- `pytest tests/integration/test_order_audit_integration.py -q`
- `pytest tests/integration/test_backtest_run_api_integration.py -q`
- `pytest tests/integration/test_live_runtime_api_integration.py -q`

### Frontend validation
- `cd frontend && npm run lint`
- `cd frontend && npm run build`
- `cd frontend && npm run test:e2e`

### Manual verification
- dashboard에서 recent live session 목록과 detail dialog 확인
- 백테스트 실행 후 `/api/v1/order-audit?scope=backtest&owner_id={run_id}` 조회
- live paper session start/stop 후 `/api/v1/order-audit?scope=live_session&owner_id={session_id}` 조회
- retention preview가 삭제 후보만 반환하고 실제 파일/row를 삭제하지 않는지 확인
- confirm 없는 prune 요청이 거절되는지 확인

## Recommended PR Slices

1. Session history frontend UX
2. Order audit repository, migration, route
3. Backtest/live audit wiring
4. Queue status, retention operations, runs UI
5. Architecture docs and runbook alignment

## Risks and Fallbacks

- Audit sink가 trading step 내부에 과도하게 침투할 수 있다.

대응:
- event-to-record 변환 helper와 optional sink를 사용하고, core order/risk 로직은 변경하지 않는다.

- Supabase migration 적용 전 API가 order audit table을 찾지 못할 수 있다.

대응:
- repository factory는 명확한 오류를 반환하고, deploy runbook에 migration 순서를 추가한다.

- retention prune이 운영 데이터를 삭제할 위험이 있다.

대응:
- preview와 prune을 분리하고, prune에는 explicit confirm과 cutoff/status 조건을 요구한다.

- frontend dashboard가 과밀해질 수 있다.

대응:
- session history는 접이식 패널 또는 compact table로 제한하고, order audit 상세는 run/session detail에서 조회한다.
