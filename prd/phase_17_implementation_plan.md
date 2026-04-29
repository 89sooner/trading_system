# Phase 17 Implementation Plan

관련 문서:
- 제품 요구사항: `prd/phase_17_prd.md`
- 실행 추적: `prd/phase_17_task.md`
- 이전 phase 실행 검증: `prd/phase_16_task.md`

## Goal

Phase 17의 구현 목표는 백테스트 실행을 API process 내부 queue에서 durable job/worker contract로 확장하고, 장시간 실행의 progress, heartbeat, cancel, stalled recovery를 운영자가 볼 수 있게 하는 것이다.

핵심 구현 원칙:

1. 새 외부 queue dependency 없이 file/Supabase 저장소 위에 job contract를 둔다.
2. 기존 `POST /api/v1/backtests`, run list/detail, API-owned dispatcher 경로의 하위 호환을 유지한다.
3. worker orchestration metadata는 backtest 결과 계산에 영향을 주지 않는다.
4. file repository와 Supabase repository는 같은 claim/lease/cancel semantics를 제공한다.
5. frontend는 상태를 과장하지 않고 worker heartbeat freshness와 progress를 그대로 표시한다.

## Preconditions

- Phase 16의 live session history와 order audit 저장소 변경은 baseline이다.
- `BacktestRunDTO`는 현재 terminal result 중심 DTO이므로 job metadata를 추가할 때 기존 result deserialization과 list item contract를 깨지 않아야 한다.
- API route의 `_to_app_settings()` validation helper를 worker에서도 재사용하거나 동일 semantics로 분리해야 한다.
- file repository는 local filesystem 전용 durable queue로 간주한다. 다중 호스트 worker는 Supabase repository에서만 지원한다.
- frontend 변경 시 `frontend/AGENTS.md`의 Next.js 버전 경고를 확인한 뒤 기존 App Router 패턴을 따른다.

## Locked Design Decisions

### 1. Job queue는 `backtest_jobs` contract로 run result와 분리한다

run result DTO에 모든 worker 필드를 섞지 않고 `BacktestJobRecord`를 새 contract로 둔다. API response는 필요한 job summary를 run DTO에 조합하지만, result 저장과 job orchestration 저장은 별도 책임으로 유지한다.

### 2. API dispatcher와 CLI worker는 같은 repository method를 사용한다

기존 `BacktestRunDispatcher.submit()`는 in-memory queue에 payload를 넣지 않는다. API가 job을 enqueue하고 dispatcher thread 또는 CLI worker가 `claim_next()`로 가져간다. 이 구조가 있어야 process restart 후 queued job을 보존할 수 있다.

### 3. Payload 저장은 API request JSON을 canonical source로 삼는다

worker는 저장된 request JSON을 `BacktestRunRequestDTO.model_validate()`로 복원한 뒤 `_to_app_settings()`와 `_to_run_metadata()`에 준하는 helper를 사용한다. `AppSettings` 객체 자체를 pickle하거나 파일 경로에 의존하지 않는다.

### 4. `cancelled` terminal status를 명시적으로 추가한다

취소는 failure와 다르므로 run/job status에 `cancelled`를 추가한다. analytics route와 frontend status badge는 cancelled run을 terminal non-success 상태로 처리한다.

### 5. Progress update는 throttled callback으로 제한한다

`run_backtest()`는 처리된 bar마다 callback을 호출할 수 있지만 worker boundary에서 시간 또는 bar count 기준으로 저장소 write를 throttle한다. unit tests에서는 throttle을 끄거나 deterministic clock을 주입한다.

## Contract Deltas

## A. Durable job repository contract

대상:
- `src/trading_system/backtest/jobs.py`
- `src/trading_system/backtest/repository.py`
- `src/trading_system/backtest/file_repository.py`
- `src/trading_system/backtest/supabase_repository.py`
- `scripts/migrations/006_add_backtest_jobs.sql`

필수 변화:
- `BacktestJobRecord`, `BacktestJobProgress`, `BacktestWorkerSnapshot` 추가
- enqueue/claim_next/heartbeat/update_progress/request_cancel/complete/fail/list_active/counts 추가
- file repository는 lock 아래 index update와 per-job payload 파일을 원자적으로 갱신
- Supabase repository는 `backtest_jobs` table과 indexes를 사용해 원자 claim 구현

비고:
- 기존 `BacktestRunRepository` protocol을 과도하게 넓히지 않고 job-specific protocol을 별도 정의한다.

## B. Worker execution contract

대상:
- `src/trading_system/app/backtest_worker.py`
- `src/trading_system/backtest/dispatcher.py`
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/server.py`

필수 변화:
- API create route가 run queued record와 job record를 함께 저장
- dispatcher가 repository-backed worker loop로 job을 claim
- CLI worker가 같은 executor를 사용
- failed/cancelled/succeeded terminal transition을 run repository와 job repository에 함께 저장
- startup recovery가 queued run을 failed로 바꾸지 않고 stale running lease만 회복 대상으로 처리

비고:
- API-owned dispatcher는 compatibility mode로 남기되 durable job contract를 사용한다.

## C. Progress and cancellation contract

대상:
- `src/trading_system/backtest/engine.py`
- `src/trading_system/app/services.py`
- `src/trading_system/backtest/dto.py`
- `src/trading_system/api/schemas.py`

필수 변화:
- `run_backtest()`에 optional `progress_callback`과 `cancel_check` 추가
- `AppServices.run()`이 callback을 전달할 수 있게 확장
- `BacktestRunDTO.cancelled()` factory 추가
- run status literal에 `cancelled` 추가
- cancellation 요청 시 queued는 즉시 cancelled, running은 cooperative cancellation으로 terminal 처리

비고:
- progress/cancel hook은 테스트에서 기본값 None일 때 기존 deterministic result와 동일해야 한다.

## D. API and frontend visibility contract

대상:
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/schemas.py`
- `frontend/lib/api/types.ts`
- `frontend/lib/api/backtests.ts`
- `frontend/app/runs/page.tsx`
- `frontend/app/runs/[runId]/page.tsx`

필수 변화:
- worker/queue status DTO가 queued/running/stale/oldest age/count를 반환
- run list/detail DTO가 optional job summary/progress를 포함
- `POST /api/v1/backtests/{run_id}/cancel` 추가
- frontend run list에 progress/stalled/cancel state 표시
- run detail에 progress panel과 cancel action 추가

비고:
- terminal run에서 cancel button은 disabled 처리한다.

## E. Documentation and release gate contract

대상:
- `README.md`
- `docs/architecture/overview.ko.md`
- `docs/architecture/overview.md`
- `docs/architecture/workspace-analysis.ko.md`
- `docs/architecture/workspace-analysis.md`
- `docs/architecture/user-use-cases.ko.md`
- `docs/architecture/user-use-cases.md`
- `docs/runbooks/deploy-production.ko.md`
- `docs/runbooks/deploy-production.md`
- `docs/runbooks/release-gate-checklist.ko.md`
- `docs/runbooks/release-gate-checklist.md`

필수 변화:
- long-running backtest gap을 durable worker 구현 상태로 갱신
- worker 실행 명령과 Supabase migration 006 적용 절차 추가
- file repository worker의 단일 호스트 제한 명시
- cancel/progress/lease recovery 검증 절차 추가

비고:
- live session retention과 KIS cancel/replace는 여전히 후속 backlog로 남긴다.

## Sequenced Implementation

### Step 0. Durable job model and repository parity

목적:
- run result와 분리된 durable backtest job contract를 만든다.

파일:
- `src/trading_system/backtest/jobs.py`
- `src/trading_system/backtest/repository.py`
- `src/trading_system/backtest/file_repository.py`
- `src/trading_system/backtest/supabase_repository.py`
- `scripts/migrations/006_add_backtest_jobs.sql`
- `tests/unit/test_backtest_jobs.py`
- `tests/unit/test_file_repository.py`
- `tests/unit/test_supabase_repository.py`

구체 작업:
- `BacktestJobRecord`, `BacktestJobProgress`, `BacktestJobListResult`, `BacktestJobRepository` protocol을 추가한다.
- job status를 `queued`, `running`, `succeeded`, `failed`, `cancelled`로 고정한다.
- file repository에 job index/payload 저장, atomic claim, heartbeat, progress, cancel, complete/fail 구현을 추가한다.
- Supabase migration 006에 `backtest_jobs` table, `run_id` FK 또는 unique reference, status/available_at/lease index, RLS deny policy를 추가한다.
- Supabase repository에 claim query와 heartbeat/progress/cancel update를 추가한다.
- file/Supabase repository parity unit tests로 claim 중복 방지, lease 만료 재claim, cancel flag, max attempts를 검증한다.

종료 조건:
- 저장소별 job lifecycle unit tests가 같은 semantics로 통과한다.

### Step 1. API enqueue and repository-backed dispatcher

목적:
- API create route와 기존 dispatcher가 durable job repository를 사용하게 한다.

파일:
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/backtest/dispatcher.py`
- `src/trading_system/api/server.py`
- `src/trading_system/api/schemas.py`
- `tests/unit/test_backtest_dispatcher.py`
- `tests/unit/test_api_server.py`
- `tests/integration/test_backtest_run_api_integration.py`

구체 작업:
- `_create_job_repository()` factory를 추가하고 app state에 연결한다.
- `create_backtest_run()`이 canonical request payload JSON을 job으로 enqueue하도록 변경한다.
- dispatcher thread가 queue.Queue 대신 `claim_next(worker_id, lease_seconds)` polling loop를 사용하게 한다.
- startup recovery가 모든 queued run을 failed로 바꾸는 기존 동작을 제거하고, stale running job만 lease 기반 recovery 대상으로 둔다.
- existing no-dispatcher fallback 테스트는 synchronous execution 또는 inline worker helper로 유지한다.
- API integration test에서 queued job payload가 저장되고 dispatcher가 claim해 terminal run을 저장하는지 검증한다.

종료 조건:
- API-owned dispatcher가 durable job contract로 run을 처리하고, process restart simulation에서 queued payload가 보존된다.

### Step 2. Out-of-process worker entrypoint

목적:
- API 서버와 분리된 프로세스가 백테스트 job을 실행할 수 있게 한다.

파일:
- `src/trading_system/app/backtest_worker.py`
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/backtest/dispatcher.py`
- `tests/unit/test_backtest_worker.py`
- `tests/integration/test_backtest_orchestration_integration.py`

구체 작업:
- worker CLI parser에 `--worker-id`, `--poll-interval`, `--lease-seconds`, `--once`, `--max-jobs`를 추가한다.
- worker가 runtime env를 로드하고 run/job/order audit repository를 조립하게 한다.
- 저장된 request payload를 DTO로 복원하고 기존 settings validation path를 통과시킨다.
- worker가 succeeded/failed terminal run과 job status를 저장하게 한다.
- `--once` smoke test로 한 job claim -> terminal 저장 경로를 검증한다.

종료 조건:
- CLI worker를 한 번 실행해 queued job 하나를 terminal state로 처리하는 테스트가 통과한다.

### Step 3. Progress heartbeat and cooperative cancellation

목적:
- 장시간 실행 중 상태를 저장하고 취소 요청을 반영한다.

파일:
- `src/trading_system/backtest/engine.py`
- `src/trading_system/app/services.py`
- `src/trading_system/backtest/dto.py`
- `src/trading_system/backtest/dispatcher.py`
- `src/trading_system/app/backtest_worker.py`
- `tests/unit/test_backtest_engine.py`
- `tests/unit/test_backtest_worker.py`
- `tests/integration/test_backtest_orchestration_integration.py`

구체 작업:
- `run_backtest()`에 total bars 계산을 깨지 않는 progress callback contract를 추가한다.
- `AppServices.run()`에 optional `progress_callback`과 `cancel_check` 인자를 추가한다.
- worker가 heartbeat와 progress를 저장하되 write throttle을 적용한다.
- `BacktestCancelled` 같은 내부 exception 또는 sentinel을 정의해 cooperative cancel을 terminal cancelled로 매핑한다.
- queued cancel과 running cancel regression test를 추가한다.
- hook이 None일 때 기존 happy-path backtest snapshot이 변하지 않는지 검증한다.

종료 조건:
- progress가 저장되고 cancel 요청이 queued/running 상태에서 deterministic terminal cancelled로 이어진다.

### Step 4. API status, cancel route, and frontend visibility

목적:
- 운영자가 API/UI에서 queue health와 run progress를 판단할 수 있게 한다.

파일:
- `src/trading_system/api/schemas.py`
- `src/trading_system/api/routes/backtest.py`
- `frontend/lib/api/types.ts`
- `frontend/lib/api/backtests.ts`
- `frontend/app/runs/page.tsx`
- `frontend/app/runs/[runId]/page.tsx`
- `frontend/components/domain/StatusBadge.tsx`
- `frontend/e2e/mocks/handlers.ts`
- `frontend/e2e/smoke.spec.ts`
- `tests/unit/test_api_backtest_schema.py`
- `tests/unit/test_backtest_retention_routes.py`
- `tests/integration/test_backtest_run_api_integration.py`

구체 작업:
- dispatcher/worker status DTO에 durable queue counts, stale count, oldest queued age를 추가한다.
- run list/detail DTO에 `job` 또는 `progress` summary를 optional field로 추가한다.
- `POST /api/v1/backtests/{run_id}/cancel` route를 추가한다.
- frontend API client와 type을 확장한다.
- `/runs` table에 progress percent, worker heartbeat freshness, stalled indicator를 추가한다.
- run detail에 progress panel과 cancel button을 추가한다.
- Playwright smoke에서 running run progress와 cancel button rendering을 검증한다.

종료 조건:
- API와 frontend가 active backtest progress/cancel/stalled 정보를 표시하고 관련 smoke test가 통과한다.

### Step 5. Documentation and release gates

목적:
- architecture와 운영 문서를 새 durable worker contract와 일치시킨다.

파일:
- `README.md`
- `docs/architecture/overview.ko.md`
- `docs/architecture/overview.md`
- `docs/architecture/workspace-analysis.ko.md`
- `docs/architecture/workspace-analysis.md`
- `docs/architecture/user-use-cases.ko.md`
- `docs/architecture/user-use-cases.md`
- `docs/runbooks/deploy-production.ko.md`
- `docs/runbooks/deploy-production.md`
- `docs/runbooks/release-gate-checklist.ko.md`
- `docs/runbooks/release-gate-checklist.md`

구체 작업:
- architecture docs에서 backtest execution baseline과 남은 gap을 갱신한다.
- README에 worker CLI 실행 예시와 API-owned dispatcher compatibility 설명을 추가한다.
- deploy runbook에 migration 006, API 서버/worker 동일 env 설정, worker smoke 절차를 추가한다.
- release gate checklist에 job claim, progress, cancel, stale recovery, frontend smoke 항목을 추가한다.

종료 조건:
- 문서가 durable worker 실행/검증 방법을 실제 코드 contract와 일치하게 설명한다.

## Validation Matrix

### Required unit tests
- `pytest tests/unit/test_backtest_jobs.py -q`
- `pytest tests/unit/test_backtest_dispatcher.py -q`
- `pytest tests/unit/test_backtest_worker.py -q`
- `pytest tests/unit/test_backtest_engine.py -q`
- `pytest tests/unit/test_file_repository.py -q`
- `pytest tests/unit/test_supabase_repository.py -q`
- `pytest tests/unit/test_api_backtest_schema.py -q`
- `pytest tests/unit/test_api_server.py -q`

### Required integration tests
- `pytest tests/integration/test_backtest_run_api_integration.py -q`
- `pytest tests/integration/test_backtest_orchestration_integration.py -q`
- `pytest tests/integration/test_trade_analytics_api_integration.py -q`

### Frontend validation
- `cd frontend && npm run lint`
- `cd frontend && npm run build`
- `cd frontend && npm run test:e2e`

### Broader regression
- `python -m compileall -q src/trading_system`
- `ruff check src/trading_system tests`
- 기존 backtest analytics와 order audit owner flow 회귀 테스트

### Manual verification
- API 서버를 실행하고 worker를 별도 프로세스로 실행해 queued run이 terminal state로 바뀌는지 확인
- worker 중단 후 lease 만료 시간이 지난 running job이 재claim되는지 확인
- `/runs`에서 progress와 heartbeat freshness가 표시되는지 확인
- running run cancel 요청 후 cancelled terminal 상태가 표시되는지 확인
- Supabase 환경에서 migration 006 적용 후 claim 중복이 없는지 확인

## Recommended PR Slices

1. Job model, migration, file/Supabase repository parity
2. API enqueue와 repository-backed dispatcher compatibility
3. CLI worker와 payload reconstruction
4. Progress/cancel hook과 terminal cancelled status
5. API/frontend visibility와 smoke tests
6. Documentation, runbook, release gate alignment

## Risks and Fallbacks

- file repository claim이 다중 호스트에서 안전하지 않을 수 있다.

대응:
- file repository worker는 단일 호스트 운영으로 문서화하고, 다중 worker/host는 Supabase를 권장한다.

- progress update가 저장소 쓰기량을 크게 늘릴 수 있다.

대응:
- worker boundary에서 throttle 기본값을 두고 unit test에서는 deterministic clock으로 검증한다.

- running cancel이 즉시 중단되지 않을 수 있다.

대응:
- cooperative cancellation이라고 UI와 docs에 명시하고, data loading 같은 긴 blocking 구간은 후속 개선으로 남긴다.

- 기존 dispatcher recovery behavior 변경으로 테스트 기대가 바뀐다.

대응:
- queued run은 보존, expired running lease는 재claim, unrecoverable legacy running run은 failed로 처리하는 새 rule을 테스트로 고정한다.

- Supabase claim query의 locking semantics가 환경별로 다르게 동작할 수 있다.

대응:
- `FOR UPDATE SKIP LOCKED` 기반 transaction test를 mock 수준과 실제 SQL contract 문서로 모두 고정하고, fallback path는 단일 worker mode로 제한한다.
