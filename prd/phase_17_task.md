# Phase 17 Task Breakdown

## Usage

- 이 파일은 Phase 17 구현 진행 상황과 검증 증적을 기록한다.
- 체크박스는 실제 구현 작업과 검증 기준을 뜻한다.
- 각 slice가 끝날 때 `Execution Log`를 갱신한다.
- PRD 수준 범위는 `phase_17_prd.md`를 기준으로 한다.
- 상세 설계와 순서는 `phase_17_implementation_plan.md`를 기준으로 한다.

## Status Note

- 이 문서는 `prd/phase_17_prd.md`의 실행 추적 문서다.
- 현재 체크박스는 active backlog를 slice 단위로 분해한 것이며, 아직 구현 완료를 의미하지 않는다.
- 이번 phase의 핵심은 durable backtest job contract, out-of-process worker, progress/heartbeat/cancel, frontend operator visibility다.

## Phase 17-0. Durable job model and repository parity

- [x] `BacktestJobRecord`, `BacktestJobProgress`, `BacktestJobRepository` contract 추가
- [x] job status를 `queued`, `running`, `succeeded`, `failed`, `cancelled`로 고정
- [x] file repository job index/payload 저장과 atomic claim 구현
- [x] file repository heartbeat/progress/cancel/complete/fail 구현
- [x] Supabase migration `006_add_backtest_jobs.sql` 작성
- [x] Supabase repository claim/heartbeat/progress/cancel/complete/fail 구현
- [x] file/Supabase claim 중복 방지 테스트 추가
- [x] lease 만료 재claim, max attempts, cancel flag repository parity 테스트 추가

Exit criteria:
- 저장소별 job lifecycle unit tests가 같은 claim/lease/cancel semantics로 통과한다.

## Phase 17-1. API enqueue and repository-backed dispatcher

- [x] app state에 backtest job repository factory 연결
- [x] `POST /api/v1/backtests`가 run queued record와 durable job payload를 함께 저장
- [x] canonical request payload JSON 저장 및 DTO 복원 helper 추가
- [x] `BacktestRunDispatcher`가 in-memory queue 대신 repository-backed claim loop를 사용
- [x] startup recovery가 queued run을 failed로 바꾸지 않도록 변경
- [x] stale running lease recovery rule 테스트 추가
- [x] API integration에서 queued payload 보존과 dispatcher terminal 저장 검증

Exit criteria:
- API-owned dispatcher가 durable job contract로 run을 처리하고 API 재시작 시 queued payload가 보존된다.

## Phase 17-2. Out-of-process worker entrypoint

- [x] `src/trading_system/app/backtest_worker.py` 추가
- [x] worker CLI에 `--worker-id`, `--poll-interval`, `--lease-seconds`, `--once`, `--max-jobs` 추가
- [x] worker가 runtime env, run repository, job repository, order audit repository를 조립
- [x] worker가 저장된 payload를 `BacktestRunRequestDTO`로 복원하고 `AppSettings`로 변환
- [x] worker가 succeeded/failed/cancelled terminal run과 job status를 저장
- [x] `--once` mode로 queued job 하나를 terminal 처리하는 테스트 추가
- [x] worker lifecycle graceful shutdown behavior 테스트 추가

Exit criteria:
- API 서버와 분리된 CLI worker가 durable queued job 하나를 claim하고 terminal state로 저장한다.

## Phase 17-3. Progress heartbeat and cooperative cancellation

- [x] `run_backtest()` optional progress callback 추가
- [x] `run_backtest()` optional cancel check 추가
- [x] `AppServices.run()`이 progress/cancel hook을 전달하도록 확장
- [x] worker heartbeat가 lease와 `last_heartbeat_at`을 갱신하도록 구현
- [x] worker progress update에 throttle 적용
- [x] `BacktestRunDTO.cancelled()` factory와 cancelled status serialization 추가
- [x] queued cancel은 즉시 cancelled 처리
- [x] running cancel은 다음 cancel check에서 cancelled 처리
- [x] hook이 None일 때 기존 deterministic backtest snapshot이 변하지 않는지 테스트

Exit criteria:
- progress가 저장되고 queued/running cancel 요청이 결정적인 terminal cancelled 상태로 이어진다.

## Phase 17-4. API status, cancel route, and frontend visibility

- [x] worker/queue status DTO에 queued/running/stale/oldest queued age/count 추가
- [x] run list DTO에 optional job progress summary 추가
- [x] run detail DTO에 worker id, lease, heartbeat, progress, cancel flag 추가
- [x] `POST /api/v1/backtests/{run_id}/cancel` route 추가
- [x] terminal run cancel 요청은 idempotent no-op 또는 structured validation error로 고정
- [x] frontend API types/client 갱신
- [x] `/runs` table에 progress, heartbeat freshness, stalled indicator 추가
- [x] run detail에 progress panel과 cancel button 추가
- [x] Playwright smoke에 running progress와 cancel button rendering 추가

Exit criteria:
- API와 frontend에서 active backtest progress/cancel/stalled 정보를 확인할 수 있고 smoke test가 통과한다.

## Phase 17-5. Documentation and release gates

- [x] `docs/architecture/overview.ko.md`와 `overview.md`에 durable worker execution 상태 반영
- [x] `docs/architecture/workspace-analysis.ko.md`와 `workspace-analysis.md`의 distributed execution gap 갱신
- [x] `docs/architecture/user-use-cases.ko.md`와 `user-use-cases.md`에 worker/progress/cancel 유즈케이스 추가
- [x] README에 worker CLI 실행 예시와 compatibility mode 설명 추가
- [x] deploy production runbook에 migration 006과 worker process smoke 절차 추가
- [x] release gate checklist에 claim/progress/cancel/stale recovery 검증 추가
- [x] file repository worker의 단일 호스트 제한과 Supabase 권장 조건 문서화

Exit criteria:
- architecture docs와 runbook이 Phase 17 구현 후 durable backtest worker contract를 실제 코드와 일치하게 설명한다.

## Verification Checklist

### Required unit tests

- [x] `pytest tests/unit/test_backtest_jobs.py -q`
- [x] `pytest tests/unit/test_backtest_dispatcher.py -q`
- [x] `pytest tests/unit/test_backtest_worker.py -q`
- [x] `pytest tests/unit/test_backtest_engine.py -q`
- [x] `pytest tests/unit/test_file_repository.py -q`
- [x] `pytest tests/unit/test_supabase_repository.py -q`
- [x] `pytest tests/unit/test_api_backtest_schema.py -q`
- [x] `pytest tests/unit/test_api_server.py -q`

### Required integration tests

- [x] `pytest tests/integration/test_backtest_run_api_integration.py -q`
- [x] `pytest tests/integration/test_backtest_orchestration_integration.py -q`
- [x] `pytest tests/integration/test_trade_analytics_api_integration.py -q`

### Frontend validation

- [x] `cd frontend && npm run lint`
- [x] `cd frontend && npm run build`
- [x] `cd frontend && npm run test:e2e`

### Broader regression

- [x] `python -m compileall -q src/trading_system`
- [x] `ruff check src/trading_system tests`
- [x] 기존 backtest analytics와 order audit owner flow 회귀 테스트 실행

### Manual verification

- [x] 별도 worker process smoke로 queued run이 terminal state로 전환되는지 확인
- [ ] worker 중단 후 lease 만료 시간이 지난 running job이 재claim되는지 확인
- [ ] `/api/v1/backtests/dispatcher` 또는 worker status route에서 durable queue counts 확인
- [ ] `/runs`에서 progress와 heartbeat freshness 표시 확인
- [ ] running run cancel 요청 후 cancelled terminal 상태 확인
- [ ] Supabase 사용 환경에서 migration 006 적용 후 동시 worker claim 중복이 없는지 확인

## Execution Log

### Date
- 2026-04-28

### Owner
- Codex

### Slice completed
- Phase 17-0: durable job model and repository parity
- Phase 17-1: API enqueue and repository-backed dispatcher
- Phase 17-2: out-of-process worker entrypoint
- Phase 17-3: progress heartbeat and cooperative cancellation
- Phase 17-4: API/frontend visibility
- Phase 17-5: docs and release gate alignment

### Scope implemented
- Added durable backtest job DTOs, file/Supabase job repository methods, and migration 006.
- Rewired API backtest creation to enqueue durable job payloads and added repository-backed dispatcher mode.
- Added standalone `trading_system.app.backtest_worker` CLI.
- Added throttled progress callbacks, heartbeat updates, cooperative cancellation, cancelled status, and cancel route.
- Added graceful SIGINT/SIGTERM shutdown handling for the standalone worker.
- Added frontend run progress/worker visibility and cancel action.
- Updated README, architecture docs, deploy runbooks, release gate checklist, and this task log.

### Files changed
- `src/trading_system/backtest/jobs.py`
- `src/trading_system/backtest/file_repository.py`
- `src/trading_system/backtest/supabase_repository.py`
- `src/trading_system/backtest/dispatcher.py`
- `src/trading_system/backtest/engine.py`
- `src/trading_system/backtest/dto.py`
- `src/trading_system/app/services.py`
- `src/trading_system/app/backtest_worker.py`
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/routes/analytics.py`
- `src/trading_system/api/schemas.py`
- `src/trading_system/api/server.py`
- `scripts/migrations/006_add_backtest_jobs.sql`
- `frontend/lib/api/types.ts`
- `frontend/lib/api/backtests.ts`
- `frontend/app/runs/page.tsx`
- `frontend/app/runs/[runId]/page.tsx`
- `frontend/components/domain/StatusBadge.tsx`
- `frontend/store/runsStore.ts`
- `frontend/e2e/mocks/handlers.ts`
- `tests/unit/test_backtest_jobs.py`
- `tests/unit/test_backtest_worker.py`
- `README.md`
- `docs/architecture/*`
- `docs/runbooks/deploy-production*`
- `docs/runbooks/release-gate-checklist*`

### Commands run
- `python -m compileall -q src/trading_system` -> passed
- `pytest tests/unit/test_backtest_jobs.py tests/unit/test_backtest_worker.py tests/unit/test_file_repository.py tests/unit/test_supabase_repository.py tests/unit/test_backtest_dispatcher.py tests/unit/test_backtest_engine.py tests/unit/test_backtest_retention_routes.py -q` -> `55 passed, 1 skipped`
- `pytest tests/unit/test_backtest_worker.py tests/unit/test_backtest_jobs.py tests/unit/test_backtest_dispatcher.py -q` -> `13 passed`
- `pytest tests/unit/test_backtest_jobs.py tests/unit/test_backtest_worker.py tests/unit/test_file_repository.py tests/unit/test_supabase_repository.py tests/unit/test_backtest_dispatcher.py tests/unit/test_backtest_engine.py tests/unit/test_backtest_retention_routes.py -q` -> `57 passed, 1 skipped`
- `pytest tests/integration/test_backtest_orchestration_integration.py -q` -> `5 passed`
- `pytest tests/integration/test_order_audit_integration.py -q` -> `3 passed`
- `pytest tests/unit/test_api_server.py::test_create_app_defers_recovery_until_lifespan_start -q` -> `1 passed`
- `ruff check src/trading_system tests --fix` -> fixed import ordering
- `ruff check src/trading_system tests` -> passed
- `ruff check src/trading_system/api/routes/backtest.py src/trading_system/app/backtest_worker.py tests/unit/test_backtest_worker.py` -> passed
- `pytest tests/unit/test_api_backtest_schema.py tests/unit/test_api_server.py tests/integration/test_backtest_run_api_integration.py tests/integration/test_trade_analytics_api_integration.py tests/integration/test_api_security_and_validation_integration.py tests/integration/test_run_persistence_integration.py -q` -> `22 passed`
- `python scripts/backtest_worker_smoke.py` -> passed
- `python scripts/check_supabase_backtest_jobs.py` -> blocked because `DATABASE_URL` is not set in this environment
- `cd frontend && npm run lint` -> passed
- `cd frontend && npm run build` -> passed
- `cd frontend && npm run test:e2e` -> `5 passed` after adding run detail progress/worker/cancel assertions

### Validation results
- Durable file job claim, lease reclaim, progress, cancel flag, snapshot counts, worker `--once`, legacy dispatcher tests, and deterministic backtest engine tests passed.
- Worker progress updates are throttled below per-bar write volume while preserving terminal 100% progress.
- Standalone worker SIGTERM/SIGINT shutdown handling exits without claiming another job after a stop request.
- Frontend lint and production build passed.
- Playwright smoke passed across 5 tests.
- Playwright now asserts the run detail progress panel, worker id, and cancel action render.
- Direct backend smoke through `create_backtest_run(..., request=None)` produced a terminal `succeeded` run and job progress at 100%.

### Risks / follow-up
- FastAPI/Starlette TestClient hang was isolated to the AnyIO thread portal/threadpool path in this environment; API tests now use an async ASGI test client and pass.
- Progress writes are throttled by percent/time thresholds; large production runs may still need environment-tunable thresholds after observing storage write volume.
- Supabase concurrent claim behavior is SQL-backed but not verified against a live Supabase database in this pass because `DATABASE_URL` is not set.
