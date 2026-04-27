# Phase 16 Implementation Plan

관련 문서:
- 제품 요구사항: `prd/phase_16_prd.md`
- 실행 추적: `prd/phase_16_task.md`
- 이전 phase 실행 검증: `prd/phase_15_task.md`

## Goal

Phase 16의 구현 목표는 live runtime session history를 최근 목록에서 검색 가능한 운영 증적과 historical incident review workflow로 확장하는 것이다. 핵심은 session search/export, historical equity/evidence API, runtime event archive, 전용 frontend history 화면이다.

핵심 구현 원칙:

1. trading, risk, broker execution semantics는 변경하지 않는다.
2. session id를 historical review의 primary key로 유지한다.
3. runtime event archive는 incident-relevant subset만 저장한다.
4. file repository와 Supabase repository의 contract를 같은 의미로 맞춘다.
5. export는 bounded CSV/JSONL response로 제한한다.
6. active dashboard monitoring과 historical session review UI를 분리한다.

## Preconditions

- Phase 15의 order audit filter/export와 broker order id propagation이 baseline이다.
- `LiveRuntimeSessionRepository`는 현재 `save`, `get`, `list(limit)`만 제공하므로 query contract 변경이 필요하다.
- `EquityWriterProtocol.read_recent()`은 active loop writer를 통해서만 호출되며, 종료 session id 기반 reader는 없다.
- `StructuredLogger.recent_events()`는 in-memory buffer이므로 session 종료 후 incident event를 조회할 수 없다.
- Supabase 배포 환경은 migration script를 명시적으로 적용해야 하므로 새 table/index는 `scripts/migrations/005_add_live_runtime_event_archive.sql`에 기록한다.
- frontend는 Next.js App Router 구조이며, historical 화면 추가 시 `frontend/AGENTS.md`를 먼저 확인한다.

## Locked Design Decisions

### 1. Session list는 typed filter object로 확장한다

`list(limit)` 파라미터를 계속 지원하되 내부적으로 `LiveRuntimeSessionFilter` 또는 동등한 keyword contract를 사용한다. API route는 `page`, `page_size`, `sort`, `start`, `end`, `provider`, `broker`, `live_execution`, `state`, `symbol`, `has_error`를 정규화한 뒤 repository에 전달한다.

### 2. Event archive는 새 모듈로 분리한다

`live_runtime_history.py`에 event table까지 넣지 않고 `src/trading_system/app/live_runtime_events.py`를 추가한다. session record 저장소와 event archive 저장소는 별도 contract로 유지하되, API evidence route에서 조합한다.

### 3. Logger subscriber는 session runner 경계에서 연결한다

`LiveRuntimeController._run_session()`에서 loop 생성 후 event archive subscriber를 연결하고, session 종료 시 반드시 unsubscribe한다. live loop는 subscriber 실패 때문에 중단되지 않아야 한다.

### 4. Historical equity는 reader factory로 조회한다

`FileEquityWriter`와 `SupabaseEquityWriter`에 static method를 추가하기보다, session id와 storage config를 받는 작은 reader/factory를 둔다. 기존 writer protocol은 유지한다.

### 5. Evidence bundle은 summary 우선이다

`GET /api/v1/live/runtime/sessions/{session_id}/evidence`는 order audit count/recent records, archived incident count/recent events, equity point count를 반환한다. 전체 데이터 export는 별도 route 또는 기존 order audit export를 사용한다.

## Contract Deltas

## A. Live session search/export contract

대상:
- `src/trading_system/app/live_runtime_history.py`
- `src/trading_system/api/routes/live_runtime.py`
- `src/trading_system/api/schemas.py`
- `scripts/migrations/005_add_live_runtime_event_archive.sql`

필수 변화:
- session list filter와 pagination total 추가
- file/Supabase filtering parity 구현
- `/api/v1/live/runtime/sessions/export` CSV/JSONL route 추가
- invalid query validation과 limit/page clamp 추가

비고:
- 기존 `/sessions?limit=10` 소비자는 계속 동작해야 한다.

## B. Historical equity/evidence contract

대상:
- `src/trading_system/app/equity_writer.py`
- `src/trading_system/app/supabase_equity_writer.py`
- `src/trading_system/execution/order_audit.py`
- `src/trading_system/api/routes/live_runtime.py`
- `src/trading_system/api/schemas.py`

필수 변화:
- session id 기반 equity reader 추가
- session evidence DTO 추가
- order audit summary aggregation 추가
- 없는 session은 404, evidence 없음은 빈 collection으로 반환

비고:
- historical equity route는 active dashboard equity route를 대체하지 않는다.

## C. Runtime event archive contract

대상:
- `src/trading_system/app/live_runtime_events.py`
- `src/trading_system/app/live_runtime_controller.py`
- `src/trading_system/app/services.py`
- `src/trading_system/core/ops.py`

필수 변화:
- `LiveRuntimeEventRecord`와 repository protocol 추가
- file/Supabase append/list/filter 구현
- session controller가 selected runtime event를 archive에 저장
- archive append 실패 isolation

비고:
- archive 대상 event allowlist는 코드에서 명시적으로 유지한다.

## D. Frontend historical session workspace

대상:
- `frontend/lib/api/types.ts`
- `frontend/lib/api/dashboard.ts`
- `frontend/components/layout/NavBar.tsx`
- `frontend/components/dashboard/SessionHistoryPanel.tsx`
- `frontend/components/dashboard/SessionDetailDialog.tsx`
- `frontend/app/dashboard/sessions/page.tsx`
- `frontend/e2e/smoke.spec.ts`

필수 변화:
- session search/export/evidence/equity API client 추가
- dashboard 최근 panel에서 dedicated sessions route로 이동하는 링크 추가
- 전용 route에 filter controls, paginated table, detail panel 추가
- detail에서 equity chart, incident timeline, order audit summary, export action 제공
- e2e smoke에 route rendering과 filter interaction 추가

비고:
- historical 화면에서 active loop control 버튼을 제공하지 않는다.

## E. Documentation and release gate contract

대상:
- `README.md`
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
- `docs/runbooks/deploy-production.ko.md`
- `docs/runbooks/deploy-production.md`
- `docs/runbooks/release-gate-checklist.ko.md`
- `docs/runbooks/release-gate-checklist.md`

필수 변화:
- live session history 갭 설명을 구현 상태로 갱신
- session id 기반 incident review 절차 추가
- migration 005 적용 절차 추가
- release gate에 historical session review 검증 추가

비고:
- 영어/한국어 문서 쌍을 함께 갱신한다.

## Sequenced Implementation

### Step 0. Session search contract

목적:
- live session repository와 API가 장기 session history를 검색할 수 있게 한다.

파일:
- `src/trading_system/app/live_runtime_history.py`
- `src/trading_system/api/routes/live_runtime.py`
- `src/trading_system/api/schemas.py`
- `tests/unit/test_live_runtime_history.py`
- `tests/unit/test_live_runtime_routes.py`
- `tests/integration/test_live_runtime_api_integration.py`

구체 작업:
- `LiveRuntimeSessionFilter`와 `LiveRuntimeSessionListResult`를 추가한다.
- repository `list()`가 `page`, `page_size`, `sort`, `start`, `end`, `provider`, `broker`, `live_execution`, `state`, `symbol`, `has_error`를 처리하게 한다.
- file repository index filtering과 Supabase `WHERE`/`COUNT` 쿼리를 구현한다.
- API response DTO에 `total`, `page`, `page_size`를 명시한다.
- 기존 `limit` query는 page 1/page_size limit으로 호환 처리한다.
- unit/integration test에 symbol/time/state/error 필터와 total count를 추가한다.

종료 조건:
- file/Supabase repository와 route-service boundary test에서 같은 filter semantics가 검증된다.

### Step 1. Session export route

목적:
- 검색된 live session records를 운영자가 CSV/JSONL로 내려받을 수 있게 한다.

파일:
- `src/trading_system/api/routes/live_runtime.py`
- `src/trading_system/api/schemas.py`
- `tests/unit/test_live_runtime_routes.py`
- `tests/integration/test_live_runtime_api_integration.py`

구체 작업:
- `/api/v1/live/runtime/sessions/export` route를 추가한다.
- list와 같은 filters를 적용하고 `format=csv|jsonl`, `limit`을 지원한다.
- `X-Live-Session-Record-Count`, `X-Live-Session-Applied-Filters` header를 추가한다.
- invalid format과 invalid datetime/sort 테스트를 작성한다.

종료 조건:
- session export가 bounded CSV/JSONL response를 반환하고 applied filters가 검증된다.

### Step 2. Historical equity and evidence APIs

목적:
- 종료된 session id로 session review에 필요한 핵심 evidence를 조회한다.

파일:
- `src/trading_system/app/equity_writer.py`
- `src/trading_system/app/supabase_equity_writer.py`
- `src/trading_system/execution/order_audit.py`
- `src/trading_system/api/routes/live_runtime.py`
- `src/trading_system/api/schemas.py`
- `tests/unit/test_equity_timeseries.py`
- `tests/unit/test_supabase_equity_writer.py`
- `tests/unit/test_order_audit_repository.py`
- `tests/integration/test_live_runtime_api_integration.py`

구체 작업:
- file/Supabase historical equity reader를 추가한다.
- `GET /api/v1/live/runtime/sessions/{session_id}/equity` route를 추가한다.
- order audit repository에 owner/scope count 또는 bounded summary helper를 추가한다.
- `GET /api/v1/live/runtime/sessions/{session_id}/evidence` DTO를 추가한다.
- session not found와 empty evidence 케이스를 테스트한다.

종료 조건:
- active loop 없이도 종료된 session id의 equity/evidence route가 결정적으로 응답한다.

### Step 3. Runtime event archive

목적:
- incident-relevant runtime events를 session 종료 후에도 조회할 수 있게 저장한다.

파일:
- `src/trading_system/app/live_runtime_events.py`
- `src/trading_system/app/live_runtime_controller.py`
- `src/trading_system/app/services.py`
- `src/trading_system/core/ops.py`
- `scripts/migrations/005_add_live_runtime_event_archive.sql`
- `tests/unit/test_live_runtime_events.py`
- `tests/unit/test_live_runtime_controller.py`
- `tests/unit/test_live_loop.py`

구체 작업:
- `LiveRuntimeEventRecord`와 file/Supabase repository를 추가한다.
- Supabase table, indexes, RLS deny policy migration을 작성한다.
- controller가 session id, event name, severity, timestamp, correlation id, payload를 archive에 append하는 subscriber를 연결한다.
- severity/prefix allowlist와 payload redaction 유지 여부를 테스트한다.
- archive append 실패가 loop start/stop과 session finalization을 깨지 않는 regression test를 추가한다.

종료 조건:
- warning/error/risk/reconciliation/control event가 session id로 durable하게 조회되고 저장 실패가 격리된다.

### Step 4. Frontend historical session workspace

목적:
- 운영자가 브라우저에서 과거 live session을 검색하고 incident evidence를 검토할 수 있게 한다.

파일:
- `frontend/lib/api/types.ts`
- `frontend/lib/api/dashboard.ts`
- `frontend/components/layout/NavBar.tsx`
- `frontend/components/dashboard/SessionHistoryPanel.tsx`
- `frontend/components/dashboard/SessionDetailDialog.tsx`
- `frontend/app/dashboard/sessions/page.tsx`
- `frontend/e2e/smoke.spec.ts`

구체 작업:
- session list/export/evidence/equity API 타입과 client 함수를 추가한다.
- nav 또는 dashboard panel에서 `/dashboard/sessions` entry point를 추가한다.
- 전용 page에 날짜 범위, provider/broker/execution/state/symbol/error filter controls를 구현한다.
- paginated table과 detail panel/dialog를 구현한다.
- detail에 preflight summary, equity chart, incident timeline, order audit summary, session export, order audit export action을 추가한다.
- Playwright smoke에서 route 렌더링과 filter submission을 검증한다.

종료 조건:
- frontend에서 historical session 검색, detail 조회, CSV/JSONL export action이 동작하고 smoke test가 통과한다.

### Step 5. Docs and release gate alignment

목적:
- 새 historical session review workflow를 문서와 운영 체크리스트에 반영한다.

파일:
- `README.md`
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
- `docs/runbooks/deploy-production.ko.md`
- `docs/runbooks/deploy-production.md`
- `docs/runbooks/release-gate-checklist.ko.md`
- `docs/runbooks/release-gate-checklist.md`

구체 작업:
- architecture docs의 session history UX gap을 구현 상태와 남은 제한으로 갱신한다.
- user use cases에 historical session review/export 흐름을 추가한다.
- KIS runbook에 session id 기준 evidence 수집 절차를 추가한다.
- incident response에 event archive -> order audit -> broker order id 대조 순서를 추가한다.
- deploy docs에 migration 005 적용을 추가한다.
- release gate checklist에 historical session review route/API 검증을 추가한다.

종료 조건:
- docs/runbooks/release checklist가 Phase 16 구현 contract와 일치한다.

## Validation Matrix

### Required unit tests
- `pytest tests/unit/test_live_runtime_history.py -q`
- `pytest tests/unit/test_live_runtime_routes.py -q`
- `pytest tests/unit/test_live_runtime_events.py -q`
- `pytest tests/unit/test_live_runtime_controller.py -q`
- `pytest tests/unit/test_live_loop.py -q`
- `pytest tests/unit/test_equity_timeseries.py -q`
- `pytest tests/unit/test_supabase_equity_writer.py -q`
- `pytest tests/unit/test_order_audit_repository.py -q`

### Required integration tests
- `pytest tests/integration/test_live_runtime_api_integration.py -q`
- `pytest tests/integration/test_order_audit_integration.py -q`

### Frontend validation
- `cd frontend && npm run lint`
- `cd frontend && npm run build`
- `cd frontend && npm run test:e2e`

### Manual verification
- API 서버에서 `/api/v1/live/runtime/sessions`를 날짜/state/symbol filter로 조회한다.
- `/api/v1/live/runtime/sessions/export?format=csv`와 `format=jsonl`이 같은 filter를 적용하는지 확인한다.
- 종료된 paper session id로 equity/evidence route가 응답하는지 확인한다.
- warning 또는 reconciliation skip을 만든 뒤 event archive가 session detail에 표시되는지 확인한다.
- frontend `/dashboard/sessions`에서 filter, detail, session export, order audit export를 확인한다.

## Recommended PR Slices

1. Session repository filtering과 list/export API
2. Historical equity/evidence API
3. Runtime event archive와 Supabase migration
4. Frontend `/dashboard/sessions` workspace
5. Documentation/runbook/release gate update

## Risks and Fallbacks

- Runtime event archive가 너무 많은 이벤트를 저장할 수 있다.

대응:
- allowlist를 severity/prefix 기반으로 고정하고, repository list/export에 limit 상한을 둔다.

- Supabase schema migration이 배포 환경에서 누락될 수 있다.

대응:
- deploy runbook에 migration 005를 추가하고, missing table 오류 메시지를 table/script 이름까지 포함하게 한다.

- File repository index가 커지면 list/filter 비용이 커질 수 있다.

대응:
- Phase 16은 bounded pagination/export로 제한하고, retention/prune은 후속 phase로 남긴다.

- Event archive 저장 실패가 live loop 안정성을 해칠 수 있다.

대응:
- subscriber append 실패를 warning으로만 처리하고, controller finalization과 loop tick을 계속 진행하게 테스트한다.

- Historical session detail이 order audit/equity/event archive 중 일부가 없는 session에서 깨질 수 있다.

대응:
- evidence route는 session 존재 여부만 404 기준으로 삼고, missing evidence는 empty list/count 0으로 반환한다.
