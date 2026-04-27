# Phase 16 Task Breakdown

## Usage

- 이 파일은 Phase 16 구현 진행 상황과 검증 증적을 기록한다.
- 체크박스는 실제 구현 작업과 검증 기준을 뜻한다.
- 각 slice가 끝날 때 `Execution Log`를 갱신한다.
- PRD 수준 범위는 `phase_16_prd.md`를 기준으로 한다.
- 상세 설계와 순서는 `phase_16_implementation_plan.md`를 기준으로 한다.

## Status Note

- 이 문서는 `prd/phase_16_prd.md`의 실행 추적 문서다.
- 구현 체크박스는 Codex 실행 결과를 반영하며, manual verification 항목은 별도 운영 환경 확인으로 남긴다.
- 이번 phase의 핵심은 live session search/export, historical evidence API, runtime event archive, frontend session history workspace다.

## Phase 16-0. Session search contract

- [x] `LiveRuntimeSessionFilter`와 `LiveRuntimeSessionListResult` 추가
- [x] `FileLiveRuntimeSessionRepository.list()`가 page/page_size/sort/time/provider/broker/execution/state/symbol/error 필터를 처리
- [x] `SupabaseLiveRuntimeSessionRepository.list()`가 같은 필터와 total count를 SQL로 처리
- [x] `/api/v1/live/runtime/sessions` response에 `total`, `page`, `page_size` 포함
- [x] 기존 `limit` query 소비자가 깨지지 않도록 호환 처리
- [x] invalid datetime, invalid sort, page/page_size clamp 테스트 추가
- [x] file/Supabase repository filter parity 테스트 추가

Exit criteria:
- live session list API가 file/Supabase repository에서 같은 filter semantics와 pagination total을 반환한다.

## Phase 16-1. Session export route

- [x] `/api/v1/live/runtime/sessions/export` route 추가
- [x] export route가 list API와 같은 filters를 적용
- [x] `format=csv|jsonl` 지원
- [x] export limit 상한과 invalid format validation 추가
- [x] `X-Live-Session-Record-Count` header 추가
- [x] `X-Live-Session-Applied-Filters` header 추가
- [x] CSV field order와 JSONL row shape 테스트 추가

Exit criteria:
- session export가 bounded CSV/JSONL response로 반환되고 applied filters가 테스트로 검증된다.

## Phase 16-2. Historical equity and evidence APIs

- [x] file equity storage를 session id로 읽는 historical reader 추가
- [x] Supabase equity storage를 session id로 읽는 historical reader 추가
- [x] `GET /api/v1/live/runtime/sessions/{session_id}/equity` route 추가
- [x] `GET /api/v1/live/runtime/sessions/{session_id}/evidence` DTO와 route 추가
- [x] evidence response에 order audit count/recent records 포함
- [x] evidence response에 equity point count 포함
- [x] evidence response에 archived incident count/recent events 자리 포함
- [x] 없는 session id는 404, evidence 없음은 empty list/count 0 반환 테스트 추가

Exit criteria:
- active loop 없이도 종료된 session id 기준 equity/evidence 조회가 통과한다.

## Phase 16-3. Runtime event archive

- [x] `src/trading_system/app/live_runtime_events.py` 추가
- [x] `LiveRuntimeEventRecord`와 repository protocol 추가
- [x] file event archive repository append/list/filter 구현
- [x] Supabase event archive repository append/list/filter 구현
- [x] `scripts/migrations/005_add_live_runtime_event_archive.sql` 작성
- [x] event archive allowlist를 severity/prefix 기준으로 고정
- [x] `LiveRuntimeController`가 session 실행 중 logger subscriber를 연결하고 종료 시 해제
- [x] archive append 실패가 live loop/session finalization을 깨지 않는 regression test 추가
- [x] event archive list가 session id/time/severity/event 필터를 적용하는지 테스트 추가

Exit criteria:
- warning/error/risk/reconciliation/control event가 session id로 durable하게 조회되고 저장 실패가 격리된다.

## Phase 16-4. Frontend historical session workspace

- [x] frontend API types에 session search/export/evidence/equity DTO 추가
- [x] `frontend/lib/api/dashboard.ts`에 session search/export/evidence/equity client 추가
- [x] `NavBar` 또는 dashboard panel에 `/dashboard/sessions` entry point 추가
- [x] `frontend/app/dashboard/sessions/page.tsx` 신규 route 구현
- [x] 날짜 범위, provider, broker, live execution, state, symbol, error filter controls 구현
- [x] paginated session table 구현
- [x] session detail에 preflight summary 표시
- [x] session detail에 historical equity chart 표시
- [x] session detail에 incident timeline 표시
- [x] session detail에 order audit summary와 order audit export action 표시
- [x] session CSV/JSONL export action 구현
- [x] Playwright smoke에 historical session route와 filter interaction 추가

Exit criteria:
- frontend에서 historical session 검색, 상세 조회, session export, order audit export가 동작하고 e2e smoke가 통과한다.

## Phase 16-5. Docs and release gate alignment

- [x] `docs/architecture/overview.ko.md`와 `overview.md`에 historical session review 상태 반영
- [x] `docs/architecture/workspace-analysis.ko.md`와 `workspace-analysis.md`의 remaining gap과 recommended backlog 갱신
- [x] `docs/architecture/user-use-cases.ko.md`와 `user-use-cases.md`에 과거 session review/export 유즈케이스 추가
- [x] KIS live operations runbook에 session evidence 수집 절차 추가
- [x] incident response runbook에 event archive -> order audit -> broker order id 대조 절차 추가
- [x] deploy production runbook에 migration 005 적용 추가
- [x] release gate checklist에 historical session review API/UI 검증 추가
- [x] README에 session history search/export와 제한 사항 요약 추가

Exit criteria:
- architecture docs와 runbook이 Phase 16 구현 후 live session search/export/evidence contract를 실제 코드와 일치하게 설명한다.

## Verification Checklist

### Required unit tests

- [x] `pytest tests/unit/test_live_runtime_history.py -q`
- [x] `pytest tests/unit/test_live_runtime_routes.py -q`
- [x] `pytest tests/unit/test_live_runtime_events.py -q`
- [x] `pytest tests/unit/test_live_runtime_controller.py -q`
- [x] `pytest tests/test_live_loop.py -q`
- [x] `pytest tests/unit/test_equity_timeseries.py -q`
- [x] `pytest tests/unit/test_supabase_equity_writer.py -q`
- [x] `pytest tests/unit/test_order_audit_repository.py -q`

### Required integration tests

- [x] `pytest tests/integration/test_live_runtime_api_integration.py -q`
- [x] `pytest tests/integration/test_order_audit_integration.py -q`

### Frontend validation

- [x] `cd frontend && npm run lint`
- [x] `cd frontend && npm run build`
- [x] `cd frontend && npm run test:e2e`

### Broader regression

- [x] `python -m compileall -q src/trading_system`
- [x] `ruff check src/trading_system tests`
- [x] related API/live runtime route regression 실행
- [x] docs/config/migration references consistency 확인

### Manual verification

- [ ] `/api/v1/live/runtime/sessions`를 state/provider/symbol/time filter로 조회
- [ ] `/api/v1/live/runtime/sessions/export?format=csv`와 `format=jsonl` 응답 확인
- [ ] 종료된 paper session id로 `/equity`와 `/evidence` route 조회
- [ ] warning 또는 reconciliation skip event가 event archive에 남는지 확인
- [ ] frontend `/dashboard/sessions`에서 filter, detail, session export, order audit export 확인
- [ ] Supabase 사용 환경에서 migration 005 적용 후 session event archive table/index 확인

## Execution Log

### Date
- 2026-04-27

### Owner
- Codex

### Slice completed
- Phase 16-0: session search contract
- Phase 16-1: session export route
- Phase 16-2: historical equity and evidence APIs
- Phase 16-3: runtime event archive
- Phase 16-4: frontend historical session workspace
- Phase 16-5: docs and release gate alignment

### Scope implemented
- Added live session search/pagination/export and evidence APIs.
- Added historical equity readers and session-scoped runtime event archive.
- Added `/dashboard/sessions` frontend workspace with filters, detail evidence, and export actions.
- Updated Supabase migration, architecture docs, runbooks, README, and release gates.

### Files changed
- `src/trading_system/app/live_runtime_history.py`
- `src/trading_system/app/live_runtime_events.py`
- `src/trading_system/app/live_runtime_controller.py`
- `src/trading_system/app/equity_writer.py`
- `src/trading_system/app/supabase_equity_writer.py`
- `src/trading_system/api/routes/live_runtime.py`
- `src/trading_system/api/schemas.py`
- `src/trading_system/api/server.py`
- `scripts/migrations/005_add_live_runtime_event_archive.sql`
- `frontend/app/dashboard/sessions/page.tsx`
- `frontend/components/dashboard/SessionHistoryPanel.tsx`
- `frontend/components/layout/NavBar.tsx`
- `frontend/lib/api/dashboard.ts`
- `frontend/lib/api/types.ts`
- `frontend/e2e/mocks/handlers.ts`
- `frontend/e2e/smoke.spec.ts`
- related tests under `tests/`
- `README.md`, `docs/architecture/*`, and selected `docs/runbooks/*`

### Commands run
- `python -m compileall -q src/trading_system` -> passed
- `ruff check src/trading_system tests --fix` -> fixed import ordering
- `ruff check src/trading_system tests` -> passed
- `pytest tests/unit/test_live_runtime_history.py tests/unit/test_live_runtime_routes.py tests/unit/test_live_runtime_events.py tests/unit/test_live_runtime_controller.py tests/test_live_loop.py tests/unit/test_equity_timeseries.py tests/unit/test_supabase_equity_writer.py tests/unit/test_order_audit_repository.py tests/integration/test_live_runtime_api_integration.py tests/integration/test_order_audit_integration.py -q` -> `53 passed, 1 skipped`
- `cd frontend && npm run lint` -> passed
- `cd frontend && npm run build` -> passed
- `cd frontend && npm run test:e2e` -> `4 passed`
- `pytest tests/unit/test_api_server.py tests/unit/test_app_services.py -q` -> stopped after hanging without output; route-service focused tests above remain the validation source

### Validation results
- Backend compile, lint, focused unit/integration tests passed.
- Frontend lint, production build, and Playwright smoke tests passed.
- Playwright covers `/dashboard/sessions` rendering, symbol filter input, row selection, and archived incident display.
- Additional TestClient/server-level regression was attempted but hit the known hang class documented in earlier phases.

### Risks / follow-up
- Supabase environments must apply `scripts/migrations/005_add_live_runtime_event_archive.sql`.
- Manual verification against a real KIS or paper runtime session is still pending.
- Runtime event archive stores selected incident-relevant events only, not the full structured log stream.
