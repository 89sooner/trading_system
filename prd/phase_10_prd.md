# Phase 10 PRD

관련 문서:
- 이전 phase 범위/결과: `prd/phase_9_prd.md`
- 이전 phase 실행 검증: `prd/phase_9_task.md`
- 아키텍처 개요: `docs/architecture/overview.ko.md`
- 워크스페이스 분석: `docs/architecture/workspace-analysis.ko.md`
- 사용자 유즈케이스: `docs/architecture/user-use-cases.ko.md`
- 상세 구현 계획: `prd/phase_10_implementation_plan.md`
- 실행 추적: `prd/phase_10_task.md`

## 문서 목적

`docs/architecture` 문서군을 기준으로 현재 저장소의 가장 큰 구현 공백은 **백테스트 실행 모델이 아직 HTTP 요청 경로에서 동기적으로 수행된다는 점**이다. `workspace-analysis.ko.md`는 긴 실행이 여전히 요청 경로를 점유한다고 명시하고 있고, `user-use-cases.ko.md`도 `POST /api/v1/backtests`가 실행 완료까지 블로킹된 뒤 결과를 저장한다고 설명한다.

현재 구현은 저장소 영속화, 애널리틱스, 프론트엔드 조회 화면까지 갖추었지만, 운영자가 장시간 백테스트를 여러 번 실행하는 순간 API 워커 점유, 타임아웃 위험, 프론트엔드의 즉시 완료 가정이 동시에 드러난다. Phase 10은 이 공백을 메우기 위해 **비동기 백테스트 큐와 run lifecycle 상태 모델**을 도입하고, 백엔드와 프론트엔드가 동일한 상태 계약을 따르도록 정리한다.

## Goal

1. `POST /api/v1/backtests`가 요청 수락 시점에 즉시 `queued` 상태를 반환하고, 실제 백테스트는 백그라운드 worker가 수행하도록 전환한다.
2. 백테스트 run lifecycle을 `queued -> running -> succeeded|failed`로 명시화하고, 기존 `/api/v1/backtests`, `/api/v1/backtests/{run_id}` API에서 일관되게 조회 가능하게 만든다.
3. 프론트엔드가 더 이상 "생성 응답 = 즉시 성공"을 가정하지 않고, pending 상태를 표시하고 polling으로 최종 상태를 추적하도록 바꾼다.
4. 백테스트 엔진, 전략, 리스크, 실행 코어의 결정적 동작은 유지하고, 실행 방식만 동기에서 비동기로 바꾼다.

구현은 반드시 다음 원칙을 지켜야 한다.

- `build_services(settings).run()` 경로와 `run_backtest()` 실행 코어는 그대로 유지한다. 전략/리스크/체결 의미를 바꾸지 않는다.
- 외부 큐 인프라(Redis, Celery, RabbitMQ)를 새로 도입하지 않는다.
- 파일 기반 저장소와 Supabase 저장소 모두 동일한 lifecycle 상태를 지원해야 한다.
- CLI 백테스트 경로는 이번 phase에서 동기 실행을 유지한다. API 경로만 비동기화한다.
- run 결과가 없는 상태(`queued`, `running`)를 정상 상태로 취급하고, 프론트엔드/애널리틱스가 이를 오류로 오해하지 않도록 한다.

## Current Baseline

- `src/trading_system/api/routes/backtest.py`의 `create_backtest_run()`은 `build_services(settings)` 후 즉시 `services.run()`을 호출하고, 완료 후에만 `_RUN_REPOSITORY.save()`를 수행한다.
- 같은 라우트는 HTTP `201`과 `status="succeeded"`를 반환한다. 즉, 수락 응답과 최종 완료 상태가 구분되지 않는다.
- `src/trading_system/api/schemas.py`의 `BacktestRunAcceptedDTO`는 `succeeded|failed`만 허용하고, `queued` 상태를 표현하지 못한다.
- `BacktestRunStatusDTO`는 `running`을 허용하지만 실제 생성 경로는 `running` 레코드를 만들지 않는다.
- `src/trading_system/backtest/dto.py`의 `BacktestRunDTO`는 성공 생성자만 제공하고, `finished_at`도 사실상 terminal 상태를 전제한 문자열 필드다.
- `src/trading_system/api/server.py`에는 startup/shutdown lifecycle에서 backtest worker를 소유하거나 복구 상태를 정리하는 런타임 서비스가 없다.
- `src/trading_system/api/routes/analytics.py`는 `run.result is None`이면 무조건 404를 반환한다. 따라서 "아직 실행 중"과 "없는 run"을 구분하지 못한다.
- `frontend/app/page.tsx`는 백테스트 생성 직후 `/runs/{runId}`로 이동하고, 로컬 저장소에 즉시 완료처럼 기록한다.
- `frontend/components/domain/StatusBadge.tsx`는 `pending` 스타일은 있지만 현재 백엔드 계약과 맞는 `queued` 상태를 다루지 않는다.
- `docs/architecture/workspace-analysis.ko.md`는 "비동기 실행 모델"을 첫 번째 남은 갭으로 명시한다.

## Non-Goals

- Redis/Celery/RQ 같은 분산 작업 큐 도입
- 여러 API 인스턴스 사이의 분산 스케줄링
- 백테스트 취소, 일시정지, 재개 기능
- 진행률 퍼센트나 bar 단위 세부 progress 스트리밍
- 라이브 루프 start/stop orchestration UI
- YAML 설정 parity 확장
- reconciliation authority 개선이나 KIS open-order API 도입
- 애널리틱스 계산 로직 자체 변경

## Hard Decisions

### D-1. FastAPI 프로세스가 소유하는 in-process dispatcher를 사용한다

- 이번 phase의 핵심은 "요청 경로 비동기화"이지 "분산 작업 플랫폼 구축"이 아니다.
- 새 의존성과 운영 복잡도를 늘리지 않기 위해, API 프로세스 startup 시 worker thread를 띄우고 shutdown 시 정리하는 bounded queue 방식으로 간다.
- 단일 worker를 기본값으로 두어 파일 저장소와 Supabase 저장소 모두에서 상태 전이 순서를 단순하게 유지한다.

### D-2. Run lifecycle 상태는 기존 run repository에 그대로 저장한다

- 별도 jobs 테이블이나 별도 저장소를 추가하면 API list/detail, 프론트엔드 runs 화면, 애널리틱스 조회가 다시 분리된다.
- `BacktestRunDTO`와 repository 구현체가 `queued`, `running`, `succeeded`, `failed` 상태를 모두 표현하도록 확장하고, 같은 `/backtests` 표면에서 일관되게 제공한다.
- terminal 전에는 `result=None`, `error=None`, `finished_at=None`을 허용한다.

### D-3. 서버 재시작으로 남겨진 `queued`/`running` run은 재개하지 않고 `failed`로 정리한다

- in-process queue는 프로세스 재시작 후 작업을 이어서 실행할 수 없다.
- restart 후 이전 run을 자동 재개하려면 입력 payload 영속화, 중복 실행 방지, worker recovery 계약이 추가로 필요하다.
- 이번 phase에서는 startup 시 stranded run을 `failed`로 마킹하고, 에러 메시지에 "previous server lifecycle interrupted"를 남기는 수준으로 제한한다.

### D-4. API 계약의 truth source는 서버 상태이며, 프론트엔드는 polling으로 추적한다

- 현재 프론트엔드는 create 응답을 즉시 완료처럼 저장하지만, 비동기 모델에서는 이 방식이 맞지 않는다.
- 프론트엔드는 create 직후 `queued` 상태를 보여줄 수는 있지만, 최종 판단은 항상 `/backtests/{run_id}` 응답으로 한다.
- runs 목록도 서버 목록을 우선 사용하고, 로컬 저장소는 일시적 fallback으로만 남긴다.

### D-5. Analytics endpoint는 "없는 run"과 "아직 완료되지 않은 run"을 구분한다

- 현재는 `result is None`이면 404를 반환해 운영자가 상태를 오해한다.
- 앞으로는:
  - run 자체가 없으면 404
  - run이 `queued` 또는 `running`이면 409
  - run이 `failed`면 409와 실패 상태 메시지
  - run이 `succeeded`일 때만 analytics를 계산한다

## Product Requirements

### PR-1. 비동기 백테스트 수락 계약

- `POST /api/v1/backtests`는 검증 성공 시 즉시 HTTP `202 Accepted`를 반환한다.
- 응답 본문은 최소 `run_id`, `status="queued"`를 포함한다.
- 요청 수락 시점에 repository에 `queued` run 레코드가 먼저 저장된다.
- 수락 응답은 실제 백테스트 완료를 의미하지 않는다.

### PR-2. Run lifecycle 상태 모델

- lifecycle 상태는 `queued`, `running`, `succeeded`, `failed` 네 가지다.
- `GET /api/v1/backtests/{run_id}`는 네 상태를 모두 반환할 수 있어야 한다.
- `queued`/`running`에서는 `result=None`, `finished_at=None`을 허용한다.
- `failed`에서는 `error`가 채워져야 하고, `finished_at`이 있어야 한다.
- `GET /api/v1/backtests`의 목록 필터 `status`는 새 상태를 모두 지원해야 한다.

### PR-3. Dispatcher와 worker 실행

- API startup 시 backtest dispatcher가 시작되고 shutdown 시 안전하게 종료된다.
- dispatcher는 bounded queue에 `(run_id, request payload)` 또는 그와 동등한 실행 입력을 저장한다.
- worker는 queue에서 꺼낸 run을 `running`으로 업데이트한 뒤 `build_services(settings).run()`을 수행한다.
- 성공 시 `succeeded` 결과를 저장하고, 예외 발생 시 `failed` 상태와 에러 문자열을 저장한다.

### PR-4. Restart recovery

- 서버 startup 시 repository에 남아 있는 `queued`/`running` run을 조회한다.
- 이 run들은 모두 `failed` 상태로 갱신되고, 에러 메시지에 이전 프로세스 종료로 중단되었음을 남긴다.
- recovery 정리는 worker가 새 작업을 받기 전에 1회 수행된다.

### PR-5. Frontend pending UX

- 새 실행 화면은 create 응답이 `queued`여도 정상 흐름으로 처리해야 한다.
- run 상세 화면은 `queued`/`running`에서 polling을 지속하고, 성공 전에는 analytics 요청을 보내지 않는다.
- runs 목록은 `queued`/`running` badge를 올바르게 표시하고, active run이 있을 때는 짧은 interval로 refetch한다.
- 상태 badge는 `queued`, `running`, `succeeded`, `failed`를 명확히 구분한다.

### PR-6. Operator-visible error semantics

- analytics endpoint는 존재하지 않는 run과 아직 완료되지 않은 run을 다른 상태 코드로 응답한다.
- 프론트엔드는 실패 run과 진행 중 run을 서로 다른 메시지로 보여준다.
- README에는 "API backtest is asynchronous"와 polling 기반 조회 방식이 반영되어야 한다.

## Scope By Epic

### Epic A. Run lifecycle 모델과 저장소 확장

목표:
- repository 계층이 pending/terminal 상태를 모두 안정적으로 저장하고 조회한다.

포함:
- `BacktestRunDTO` 상태 생성자 추가
- `finished_at` nullable 처리
- file/supabase repository 직렬화/역직렬화 확장
- lifecycle 상태 필터 테스트

제외:
- 분산 queue용 별도 jobs schema
- run 취소 API

### Epic B. API dispatcher와 상태 전이

목표:
- 요청 경로에서 실행을 떼어내고 백그라운드 worker가 동일 실행 코어를 사용하도록 만든다.

포함:
- startup/shutdown dispatcher wiring
- queued 저장 후 enqueue
- running/succeeded/failed 상태 전이
- restart recovery
- analytics 409 처리

제외:
- multi-worker scheduling
- priority queue
- progress percentage 계산

### Epic C. 프론트엔드 pending 상태 UX 정렬

목표:
- 프론트엔드가 async 계약을 서버 truth source에 맞게 소비한다.

포함:
- create 화면의 queued 응답 처리
- run detail polling
- runs list active refetch
- status badge 상태 추가
- analytics gating

제외:
- 대규모 UX 리디자인
- websocket 도입

## Impacted Files

### Backtest lifecycle and repository
- `src/trading_system/backtest/dto.py`
- `src/trading_system/backtest/repository.py`
- `src/trading_system/backtest/file_repository.py`
- `src/trading_system/backtest/supabase_repository.py`
- `src/trading_system/backtest/dispatcher.py`

### API runtime and contracts
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/routes/analytics.py`
- `src/trading_system/api/server.py`
- `src/trading_system/api/schemas.py`

### Frontend run flows
- `frontend/app/page.tsx`
- `frontend/app/runs/page.tsx`
- `frontend/app/runs/[runId]/page.tsx`
- `frontend/components/domain/StatusBadge.tsx`
- `frontend/lib/api/backtests.ts`
- `frontend/lib/api/types.ts`
- `frontend/store/runsStore.ts`

### Validation and docs
- `tests/unit/test_api_backtest_schema.py`
- `tests/unit/test_backtest_dispatcher.py`
- `tests/unit/test_file_repository.py`
- `tests/unit/test_supabase_repository.py`
- `tests/integration/test_backtest_run_api_integration.py`
- `tests/integration/test_run_persistence_integration.py`
- `tests/integration/test_trade_analytics_api_integration.py`
- `README.md`

## Delivery Slices

### Slice 0. Run lifecycle DTO와 저장소 확장
- `queued`/`running`/`failed` 상태를 DTO와 repository 계층에서 저장 가능하게 만든다.

### Slice 1. Dispatcher 도입과 API async 수락
- `POST /backtests`가 queued 저장 후 즉시 202를 반환하고, worker가 실제 실행을 담당하게 만든다.

### Slice 2. Recovery와 조회 계약 정리
- startup stranded run 정리, detail/list/analytics 상태 코드를 일관되게 맞춘다.

### Slice 3. Frontend pending UX 반영
- runs 생성/목록/상세 화면이 queued/running 상태를 자연스럽게 처리하도록 바꾼다.

### Slice 4. 문서와 회귀 검증
- README와 테스트를 async 계약에 맞게 갱신하고 전체 회귀를 검증한다.

## Success Metrics

- `POST /api/v1/backtests`가 백테스트 완료를 기다리지 않고 즉시 `202`와 `queued`를 반환한다.
- 동일 run이 `queued -> running -> succeeded|failed`로 전이하는 것이 API에서 관찰된다.
- `GET /api/v1/backtests`와 `GET /api/v1/backtests/{run_id}`가 pending 상태를 정상적으로 표현한다.
- 프론트엔드에서 run 생성 직후 상세 화면이 깨지지 않고 pending 상태를 보여준 뒤 terminal 상태로 전환된다.
- analytics 요청이 완료 전 run에 대해 404가 아니라 상태 기반 응답을 반환한다.

## Risks and Follow-up

- in-process worker는 단일 API 프로세스 기준 설계다. 다중 인스턴스 배포나 분산 스케줄링은 후속 phase가 필요하다.
- restart 시 run 재개가 아니라 실패 처리로 끝나므로, durable resume이 필요하면 입력 payload 영속화가 추가로 필요하다.
- 장기적으로는 retention 정책과 run cleanup 도구가 필요하지만, 이번 phase에서는 async lifecycle 정렬을 우선한다.
- 이후 backlog로는 live loop orchestration UI, config parity, reconciliation authority 개선을 별도 phase로 분리하는 것이 맞다.
