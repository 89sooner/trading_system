# Phase 17 PRD

관련 문서:
- 이전 phase 범위/결과: `prd/phase_16_prd.md`
- 이전 phase 실행 검증: `prd/phase_16_task.md`
- 아키텍처 개요: `docs/architecture/overview.ko.md`
- 워크스페이스 분석: `docs/architecture/workspace-analysis.ko.md`
- 사용자 유즈케이스: `docs/architecture/user-use-cases.ko.md`
- 상세 구현 계획: `prd/phase_17_implementation_plan.md`
- 실행 추적: `prd/phase_17_task.md`

## 문서 목적

Phase 16까지의 완료 코드는 live runtime session history 검색/export/evidence, runtime event archive, order audit export, strategy config parity를 구현했다. `docs/architecture` 기준으로 남은 가장 큰 운영 갭은 긴 백테스트가 여전히 API 프로세스 내부 dispatcher thread와 in-memory queue에 묶여 있다는 점이다.

현재 `POST /api/v1/backtests`는 run record를 `queued`로 저장하지만 실제 실행 payload는 `QueuedBacktestRun` 객체로 메모리 queue에만 존재한다. API 프로세스가 재시작되면 `recover_interrupted_runs()`가 `queued`와 `running` run을 모두 failed로 바꾸며, 별도 worker 프로세스가 저장소에서 작업을 claim하거나 heartbeat/progress/cancel 상태를 갱신할 방법이 없다. 프론트엔드는 queue depth와 run status만 볼 수 있어 장시간 실행의 정체, worker 장애, 취소 요청을 운영자가 판단하기 어렵다.

Phase 17은 백테스트 실행을 저장소 기반 durable job contract로 승격한다. 목표는 새 외부 queue 의존성을 추가하지 않고, 파일 저장소와 Supabase 저장소 위에서 worker lease, heartbeat, progress, cancel request, stalled run recovery를 지원하는 out-of-process worker 경로를 추가하는 것이다.

## Goal

1. 백테스트 요청 payload를 durable job record로 저장해 API 프로세스 재시작 후에도 queued 작업이 사라지지 않게 한다.
2. API-owned dispatcher와 독립적인 CLI worker가 저장소에서 작업을 claim/lease하고 terminal 상태를 저장할 수 있게 한다.
3. 실행 중 run은 worker id, lease 만료 시각, heartbeat, progress, cancel_requested 상태를 노출해야 한다.
4. 운영자는 API와 프론트엔드에서 worker 상태, 진행률, stalled 여부, 취소 요청 상태를 확인할 수 있어야 한다.
5. 백테스트 엔진의 결정성은 유지하고, progress/cancel hook은 실행 결과 계산에 영향을 주지 않아야 한다.

이번 phase는 다음 원칙을 따른다.

- Redis, Celery, Kafka 같은 새 runtime dependency를 도입하지 않는다.
- file repository와 Supabase repository의 job semantics를 같은 의미로 맞춘다.
- 기존 `POST /api/v1/backtests`와 run detail 조회 contract는 하위 호환을 유지한다.
- trading step, strategy, risk, broker simulator의 매매 의미는 변경하지 않는다.
- worker heartbeat/progress 시간은 실행 orchestration metadata이며 backtest 결과 계산에 사용하지 않는다.

## Current Baseline

- `BacktestRunDispatcher`는 API process 안의 daemon thread와 `queue.Queue`로만 작업을 처리한다.
- `BacktestRunDTO`는 `queued`, `running`, `succeeded`, `failed` 상태와 결과/error만 저장하며 request payload, worker id, heartbeat, progress, cancel flag가 없다.
- `FileBacktestRunRepository`와 `SupabaseBacktestRunRepository`는 run 저장/조회/list/delete/clear만 제공한다.
- `recover_interrupted_runs()`는 재시작 시 `queued`와 `running` run을 모두 failed 처리한다. queued payload가 저장소에 없기 때문에 재시작 후 재개할 수 없다.
- `run_backtest()`는 전체 bars 반복이 끝난 뒤 결과를 반환한다. 중간 progress callback이나 cancellation check는 없다.
- `/api/v1/backtests/dispatcher`는 worker running 여부, queue depth, max queue size만 반환한다.
- 프론트엔드 `/runs`는 queued/running/succeeded count와 dispatcher capacity만 보여주며, 개별 run progress, worker heartbeat, cancel action은 없다.
- `docs/architecture/workspace-analysis.ko.md`는 "분산 실행 모델"과 "긴 backtest 운영 가시성"을 권장 다음 backlog의 첫 항목으로 둔다.

## Non-Goals

- Redis/Celery/Kafka/SQS 같은 외부 queue 서비스 도입
- 여러 호스트 간 artifact/object storage 동기화
- 부분 결과 streaming, incremental analytics, run result chunking
- 실행 중 portfolio/result snapshot resume
- 백테스트 병렬화, 심볼 단위 shard execution, distributed computation
- live runtime worker 모델 변경
- strategy promotion/approval workflow
- 인터넷 공개용 auth/RBAC 강화
- live session/event archive retention 구현
- KIS cancel/replace 또는 장기 order polling 구현

## Hard Decisions

### D-1. 저장소 기반 job queue를 추가하고 외부 queue dependency는 도입하지 않는다

이 저장소는 이미 파일 저장소와 Supabase PostgreSQL 양쪽을 지원한다. Phase 17은 두 저장소 위에 `BacktestJobRepository`를 추가해 enqueue, claim, heartbeat, progress, cancel, complete/fail semantics를 구현한다. 외부 queue 서비스는 운영 복잡도와 새 의존성을 키우므로 이번 phase 범위에서 제외한다.

### D-2. API dispatcher는 compatibility path로 유지하되 durable job contract를 사용한다

기존 API 동작과 테스트를 깨지 않기 위해 API-owned worker thread는 유지한다. 다만 submit 대상은 in-memory payload가 아니라 저장소에 저장된 job이며, API thread도 같은 claim/lease contract를 사용한다. 별도 CLI worker는 같은 repository contract를 소비한다.

### D-3. Request payload는 normalized JSON으로 저장한다

worker가 API 프로세스와 분리되어도 같은 설정을 재구성할 수 있도록 `BacktestRunRequestDTO` 또는 정규화된 동등 payload를 JSON으로 저장한다. Decimal, enum, strategy 설정은 pydantic JSON 직렬화를 통해 보존하고 worker는 기존 validation helper를 거쳐 `AppSettings`를 재구성한다.

### D-4. Progress와 cancel은 orchestration hook으로만 연결한다

`run_backtest()`에 optional progress callback과 cancellation check를 추가한다. hook은 처리된 bar 수, 전체 bar 수, 마지막 timestamp 같은 운영 metadata만 보고하며, signal/risk/order 계산에는 영향을 주지 않는다. cancel 요청은 cooperative cancellation으로 처리하고 terminal status는 `cancelled` 또는 `failed` 중 하나로 명확히 결정한다.

### D-5. Stalled recovery는 lease 만료 기준으로만 수행한다

worker heartbeat가 멈춘 작업은 lease 만료 후 다른 worker가 claim할 수 있다. 실행 중 프로세스가 죽었을 때 partial result resume은 하지 않는다. 재claim된 작업은 처음부터 다시 실행되며, deterministic backtest contract가 같은 terminal result를 만들 수 있어야 한다.

## Product Requirements

### PR-1. Durable backtest job contract

- 백테스트 생성 시 run record와 함께 job record가 저장되어야 한다.
- job record는 `run_id`, `status`, `payload`, `created_at`, `available_at`, `attempt_count`, `max_attempts`, `worker_id`, `lease_expires_at`, `last_heartbeat_at`, `progress`, `cancel_requested`, `error`를 포함해야 한다.
- file repository와 Supabase repository는 enqueue/claim/heartbeat/progress/cancel/complete/fail 동작을 같은 의미로 제공해야 한다.
- job payload가 deserialize/validation 실패하면 run은 terminal failed 상태가 되어야 한다.

### PR-2. Worker lease and recovery

- worker는 `worker_id`와 lease duration으로 다음 queued/stale job을 claim해야 한다.
- claim은 같은 job이 두 worker에 동시에 할당되지 않도록 원자적으로 동작해야 한다.
- heartbeat는 lease를 연장하고 `last_heartbeat_at`을 갱신해야 한다.
- lease 만료된 running job은 configured max attempts 전까지 재claim 가능해야 한다.
- max attempts 초과 또는 unrecoverable validation failure는 run을 failed로 저장해야 한다.

### PR-3. Out-of-process worker entrypoint

- `python -m trading_system.app.backtest_worker` 또는 동등한 CLI entrypoint가 저장소에서 job을 poll하고 실행해야 한다.
- worker는 `--worker-id`, `--poll-interval`, `--lease-seconds`, `--once`, `--max-jobs` 같은 운영 인자를 제공해야 한다.
- worker process는 existing `build_services()`와 order audit repository를 사용해 기존 실행 경로와 같은 결과를 만들어야 한다.
- graceful shutdown 시 현재 tick 이후 heartbeat를 멈추고, terminal 상태를 저장하지 못한 job은 lease 만료로 recovery될 수 있어야 한다.

### PR-4. Progress and cancellation

- run detail API는 `progress`와 worker metadata를 반환해야 한다.
- progress는 최소 `processed_bars`, `total_bars`, `percent`, `last_bar_timestamp`, `updated_at`을 포함해야 한다.
- `POST /api/v1/backtests/{run_id}/cancel`은 queued/running run에 cancel request를 기록해야 한다.
- queued run cancel은 terminal cancelled로 즉시 전환할 수 있어야 한다.
- running run cancel은 cooperative cancellation으로 처리되어야 하며, 다음 cancel check 지점에서 terminal cancelled로 저장되어야 한다.

### PR-5. API and frontend operator visibility

- `/api/v1/backtests/dispatcher` 또는 새 worker status route는 durable queue count, running leases, stale count, oldest queued age를 노출해야 한다.
- `/api/v1/backtests` list item은 active run progress summary를 포함해야 한다.
- 프론트엔드 `/runs`는 worker status, queued age, running progress, stalled indicator를 표시해야 한다.
- run detail 화면은 worker id, heartbeat freshness, progress, cancel action을 제공해야 한다.
- cancel action은 terminal run에는 비활성화되어야 한다.

### PR-6. Docs and deployment alignment

- architecture docs는 API-owned dispatcher 한계를 durable worker contract와 CLI worker 경로로 갱신해야 한다.
- README와 deploy runbook은 API 서버와 worker를 같은 repository/storage 설정으로 실행하는 절차를 설명해야 한다.
- release gate checklist는 file repository worker smoke, Supabase claim semantics, cancel/progress 검증을 포함해야 한다.

## Scope By Epic

### Epic A. Durable job model and repositories

목표:
- 백테스트 job payload와 worker lease 상태를 저장소에 영속화한다.

포함:
- job DTO/filter/snapshot 모델
- file repository atomic claim/update
- Supabase table/index/migration과 `FOR UPDATE SKIP LOCKED` 또는 동등한 claim query
- 기존 run repository와 job repository 조립 factory
- repository parity tests

제외:
- 외부 queue service
- partial result storage
- distributed artifact sync

### Epic B. Worker execution path

목표:
- API 프로세스 밖에서도 같은 백테스트 실행 경로를 사용할 수 있게 한다.

포함:
- `app.backtest_worker` CLI module
- durable job claim loop
- payload -> `AppSettings` reconstruction
- order audit repository wiring
- worker lifecycle logs
- max attempt/failure handling

제외:
- systemd/docker compose 작성 자체
- multi-host scheduling policy
- worker autoscaling

### Epic C. Progress, heartbeat, and cancellation

목표:
- 장시간 백테스트의 운영 상태를 관찰하고 중단 요청을 기록할 수 있게 한다.

포함:
- `run_backtest()` optional progress/cancel hooks
- `AppServices.run()` progress/cancel callback 전달
- job heartbeat/progress update
- queued/running cancel request
- cancelled terminal status contract
- tests for deterministic result preservation

제외:
- partial analytics rendering
- forced process kill
- resume from processed bar offset

### Epic D. API and frontend visibility

목표:
- 운영자가 브라우저와 API로 worker 상태와 run 진행률을 판단할 수 있게 한다.

포함:
- worker/queue status DTO
- run list/detail progress fields
- cancel route
- frontend `/runs` worker status/progress/stalled UI
- run detail cancel/progress panel
- Playwright smoke update

제외:
- dedicated worker admin route beyond backtest scope
- real-time websocket/SSE progress stream
- RBAC-based cancel permission

### Epic E. Docs and release gates

목표:
- 새 durable worker 운영 방식을 문서와 검증 기준에 반영한다.

포함:
- architecture docs 갱신
- README worker 실행 예시 추가
- production deploy runbook 갱신
- release gate checklist 갱신
- migration note 추가

제외:
- 별도 ADR 작성
- 외부 queue 운영 문서

## Impacted Files

### Backtest job contracts and repositories
- `src/trading_system/backtest/jobs.py`
- `src/trading_system/backtest/repository.py`
- `src/trading_system/backtest/file_repository.py`
- `src/trading_system/backtest/supabase_repository.py`
- `src/trading_system/backtest/dispatcher.py`
- `scripts/migrations/006_add_backtest_jobs.sql`
- `tests/unit/test_backtest_jobs.py`
- `tests/unit/test_file_repository.py`
- `tests/unit/test_supabase_repository.py`

### Worker execution and progress hooks
- `src/trading_system/app/backtest_worker.py`
- `src/trading_system/app/services.py`
- `src/trading_system/app/main.py`
- `src/trading_system/backtest/engine.py`
- `src/trading_system/api/routes/backtest.py`
- `tests/unit/test_backtest_worker.py`
- `tests/unit/test_backtest_engine.py`
- `tests/unit/test_backtest_dispatcher.py`
- `tests/integration/test_backtest_orchestration_integration.py`

### API schemas and routes
- `src/trading_system/api/schemas.py`
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/server.py`
- `tests/unit/test_api_backtest_schema.py`
- `tests/unit/test_backtest_retention_routes.py`
- `tests/unit/test_api_server.py`
- `tests/integration/test_backtest_run_api_integration.py`

### Frontend worker visibility
- `frontend/lib/api/types.ts`
- `frontend/lib/api/backtests.ts`
- `frontend/app/runs/page.tsx`
- `frontend/app/runs/[runId]/page.tsx`
- `frontend/components/domain/StatusBadge.tsx`
- `frontend/e2e/mocks/handlers.ts`
- `frontend/e2e/smoke.spec.ts`

### Documentation and operator notes
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

## Delivery Slices

### Slice 0. Job contract and storage
- durable job DTO, file/Supabase storage, migration, repository parity tests를 추가한다.

### Slice 1. Worker claim and execution
- API dispatcher와 CLI worker가 같은 claim/lease contract로 백테스트를 실행하게 한다.

### Slice 2. Progress and cancellation
- progress heartbeat와 cooperative cancel hook을 engine/service/worker 경계에 연결한다.

### Slice 3. API visibility
- run list/detail, worker status, cancel route에 worker metadata와 progress를 노출한다.

### Slice 4. Frontend operator workflow
- `/runs`와 run detail에서 progress, heartbeat freshness, stalled 상태, cancel action을 제공한다.

### Slice 5. Docs and release gates
- architecture, README, deploy runbook, release gate checklist를 새 worker contract와 일치시킨다.

## Success Metrics

- API 재시작 후 queued job payload가 보존되고 worker가 claim할 수 있다.
- 두 worker가 동시에 poll해도 같은 job을 중복 claim하지 않는다.
- running job heartbeat가 lease를 갱신하고 stale job은 lease 만료 후 재claim 가능하다.
- progress가 긴 run 중 최소 처리 bar 수와 percent를 API/UI에서 확인할 수 있다.
- queued cancel은 즉시 terminal cancelled로 끝나고, running cancel은 다음 cancel check 후 cancelled로 끝난다.
- 기존 synchronous fallback 또는 API-owned dispatcher 소비자는 하위 호환된다.
- focused backend tests, integration tests, frontend lint/build/e2e smoke가 통과한다.

## Risks and Follow-up

- file repository atomic claim은 단일 파일시스템 lock 수준으로 제한된다. 다중 호스트 file storage는 지원하지 않는다고 문서화하고 Supabase를 권장한다.
- Supabase claim query는 transaction semantics에 의존하므로 migration/index와 repository tests가 중요하다.
- cooperative cancel은 broker simulator나 data loading 내부의 긴 blocking 작업을 즉시 끊지 못한다.
- progress update 빈도가 과도하면 file/Supabase write amplification이 생길 수 있으므로 최소 interval 또는 bar step 기준 throttle이 필요하다.
- partial result resume, distributed compute, 외부 queue service는 후속 phase로 남긴다.
