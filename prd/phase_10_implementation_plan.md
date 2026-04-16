# Phase 10 Implementation Plan

## Goal

Phase 10의 구현 목표는 API 백테스트를 동기 요청 처리에서 분리하고, 서버와 프론트엔드가 공유하는 run lifecycle 계약을 `queued`, `running`, `succeeded`, `failed`로 재정렬하는 것이다.

핵심 구현 원칙:

1. 백테스트 계산 자체는 기존 `build_services().run()` 경로를 그대로 사용한다.
2. 상태 저장은 별도 jobs 시스템이 아니라 기존 run repository를 확장하는 방식으로 처리한다.
3. 파일 저장소와 Supabase 저장소는 동일한 lifecycle 의미를 제공해야 한다.
4. 프론트엔드는 서버를 truth source로 보고 polling으로 terminal 상태를 추적한다.
5. restart recovery는 "재개"가 아니라 "중단된 run을 failed로 정리"하는 범위로 제한한다.

## Preconditions

- Phase 9의 run persistence와 Supabase/file dual backend가 정상 동작하고 있어야 한다.
- `POST /api/v1/backtests`의 응답 코드가 `201`에서 `202`로 바뀌므로, 기존 테스트와 프론트엔드 호출부를 같은 변경 세트에서 함께 갱신해야 한다.
- `queued` 상태 추가에 따라 DTO, status badge, run detail polling, analytics gating이 동시에 바뀌어야 한다.
- CLI 경로는 이번 phase에서 비동기화하지 않는다.
- `finished_at`는 pending 상태에서 `None`이 될 수 있으므로, schema와 frontend 타입이 이 nullable 계약을 수용해야 한다.

## Locked Design Decisions

### 1. `BacktestRunDispatcher`를 새로 만들고 FastAPI lifespan에서 소유한다

- 신규 모듈 `src/trading_system/backtest/dispatcher.py`에 bounded queue와 단일 worker thread를 둔다.
- `create_app()` startup에서 dispatcher를 시작하고 `app.state.backtest_dispatcher`에 보관한다.
- shutdown에서 worker 종료 신호를 보내고 thread join을 수행한다.

### 2. Repository는 lifecycle 상태 전체를 저장하는 단일 source of truth가 된다

- `BacktestRunDTO`에 `queued`, `running`, `failed`, `succeeded` 생성자를 추가한다.
- `finished_at`는 `str | None`으로 바꾼다.
- pending 상태는 `result=None`, `error=None`, `finished_at=None`을 사용한다.

### 3. Restart recovery는 startup 1회 정리로 제한한다

- dispatcher 시작 전에 repository에서 `queued`와 `running` run을 조회해 모두 `failed`로 치환한다.
- 에러 메시지는 운영자가 원인을 이해할 수 있도록 고정된 interruption 문구를 포함한다.
- 자동 재실행은 구현하지 않는다.

### 4. Analytics endpoint는 상태 기반 오류를 반환한다

- run이 없으면 404
- run이 `queued` 또는 `running`이면 409
- run이 `failed`면 409와 실패 이유 반환
- run이 `succeeded`일 때만 analytics 계산

### 5. Frontend는 optimistic 완료가 아니라 optimistic queueing만 허용한다

- create 직후 로컬 저장소에 `queued`를 기록할 수는 있지만, 최종 상태는 항상 서버 polling 결과로 갱신한다.
- run detail은 `queued`/`running`에서 주기적으로 refetch한다.
- runs 목록은 active run 존재 시 refetch interval을 줄이고, active run이 없으면 interval을 끈다.

## Contract Deltas

## A. Backtest run DTO and repository contract

대상:
- `src/trading_system/backtest/dto.py`
- `src/trading_system/backtest/repository.py`
- `src/trading_system/backtest/file_repository.py`
- `src/trading_system/backtest/supabase_repository.py`

필수 변화:
- `BacktestRunDTO.status`가 `queued|running|succeeded|failed`를 지원해야 한다.
- `finished_at`를 nullable로 바꿔 pending 상태를 정상 표현해야 한다.
- file/supabase repository가 pending 레코드를 손실 없이 저장/조회해야 한다.
- 목록 정렬과 status 필터가 pending 상태에서도 안정적으로 동작해야 한다.

비고:
- 별도 jobs table이나 별도 repository 추가는 하지 않는다.

## B. API submission and dispatcher lifecycle

대상:
- `src/trading_system/backtest/dispatcher.py`
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/server.py`
- `src/trading_system/api/schemas.py`

필수 변화:
- `POST /api/v1/backtests`는 queued 레코드를 저장하고 dispatcher에 enqueue한 뒤 `202`를 반환해야 한다.
- worker는 dequeued 직후 `running`으로 업데이트하고, 종료 시 `succeeded|failed`로 저장해야 한다.
- startup/shutdown에서 dispatcher lifecycle과 restart recovery가 관리되어야 한다.
- `BacktestRunAcceptedDTO`와 `BacktestRunStatusDTO`가 새 상태와 nullable 필드를 반영해야 한다.

비고:
- 실행 payload는 worker가 재구성 가능한 최소 형태로 전달하되, route 함수와 동일한 설정 변환 로직을 재사용해야 한다.

## C. Analytics and status semantics

대상:
- `src/trading_system/api/routes/analytics.py`
- `tests/integration/test_trade_analytics_api_integration.py`

필수 변화:
- analytics route가 "run 없음"과 "run 미완료"를 다른 응답으로 구분해야 한다.
- 실패 run에 대한 응답 메시지가 UI에서 읽기 쉬워야 한다.

비고:
- analytics 계산 로직 자체는 바꾸지 않는다.

## D. Frontend async run UX

대상:
- `frontend/app/page.tsx`
- `frontend/app/runs/page.tsx`
- `frontend/app/runs/[runId]/page.tsx`
- `frontend/components/domain/StatusBadge.tsx`
- `frontend/lib/api/backtests.ts`
- `frontend/lib/api/types.ts`
- `frontend/store/runsStore.ts`

필수 변화:
- create 페이지가 `queued` 응답을 정상 처리해야 한다.
- detail 페이지는 pending 상태에서 polling하고 analytics를 막아야 한다.
- runs 목록은 pending 상태를 표시하고 active run이 있으면 refetch interval을 갖는다.
- badge 및 에러 메시지가 `queued`, `running`, `failed`를 구분해야 한다.

비고:
- 대규모 레이아웃 개편은 하지 않는다.

## Sequenced Implementation

### Step 0. Run lifecycle DTO와 repository 확장

목적:
- pending 상태를 저장할 수 있는 최소 계약을 먼저 고정한다.

파일:
- `src/trading_system/backtest/dto.py`
- `src/trading_system/backtest/repository.py`
- `src/trading_system/backtest/file_repository.py`
- `src/trading_system/backtest/supabase_repository.py`
- `tests/unit/test_file_repository.py`
- `tests/unit/test_supabase_repository.py`

구체 작업:
- `BacktestRunDTO`에 `queued()`, `running()`, `failed()`, `succeeded()` 생성자를 정리한다.
- `finished_at`를 `str | None`으로 바꾸고 직렬화/역직렬화 경로를 맞춘다.
- repository 테스트에 pending 상태 round-trip과 status filter 케이스를 추가한다.
- Supabase repository의 `get/list/save`가 nullable `finished_at`와 status 전이를 보존하는지 검증한다.

종료 조건:
- file/supabase repository에서 `queued`와 `running` run을 저장하고 다시 읽었을 때 상태와 nullable 필드가 유지된다.

### Step 1. Dispatcher 구현과 async POST 계약 전환

목적:
- 요청 수락과 실제 실행을 분리한다.

파일:
- `src/trading_system/backtest/dispatcher.py`
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/server.py`
- `src/trading_system/api/schemas.py`
- `tests/unit/test_backtest_dispatcher.py`
- `tests/integration/test_backtest_run_api_integration.py`

구체 작업:
- bounded queue + worker thread를 가진 dispatcher를 구현한다.
- route에서 payload 검증 후 `queued` run을 저장하고 enqueue한다.
- 응답 상태 코드를 `202 Accepted`로 바꾸고 `BacktestRunAcceptedDTO`를 `queued`에 맞춘다.
- worker가 `running` 전이 후 `build_services(settings).run()`을 실행하도록 만든다.
- 성공/예외 경로 모두 repository에 terminal 상태를 저장하게 한다.

종료 조건:
- `POST /api/v1/backtests` 호출이 실행 완료 전 즉시 반환하고, worker가 별도로 run을 terminal 상태로 전이한다.

### Step 2. Startup recovery와 조회/analytics 의미 정리

목적:
- API가 pending/failed 상태를 운영자 친화적으로 설명하도록 만든다.

파일:
- `src/trading_system/api/server.py`
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/routes/analytics.py`
- `src/trading_system/api/schemas.py`
- `tests/integration/test_run_persistence_integration.py`
- `tests/integration/test_trade_analytics_api_integration.py`

구체 작업:
- startup 시 stranded `queued`/`running` run을 `failed`로 바꾸는 recovery 함수를 추가한다.
- detail/list DTO에서 nullable `finished_at`와 pending 상태를 반환하도록 조정한다.
- analytics route에서 404/409 구분을 구현한다.
- persistence 통합 테스트에 restart recovery와 pending 상태 필터를 추가한다.

종료 조건:
- restart 후 stranded run이 실패 상태로 정리되고, analytics가 pending run에 대해 409를 반환한다.

### Step 3. Frontend pending UX 반영

목적:
- UI가 async 계약을 깨지 않고 자연스럽게 소비하도록 만든다.

파일:
- `frontend/app/page.tsx`
- `frontend/app/runs/page.tsx`
- `frontend/app/runs/[runId]/page.tsx`
- `frontend/components/domain/StatusBadge.tsx`
- `frontend/lib/api/backtests.ts`
- `frontend/lib/api/types.ts`
- `frontend/store/runsStore.ts`

구체 작업:
- create 페이지에서 응답 status를 `queued`로 저장하고 상세 페이지로 이동한다.
- detail 페이지는 `queued`/`running`에서 refetch interval을 적용한다.
- analytics query는 `succeeded`일 때만 활성화한다.
- runs 목록은 active run이 있으면 자동 refetch하고, badge 스타일을 새 상태에 맞춘다.
- 오류 문구를 pending/failed 시나리오에 맞게 정리한다.

종료 조건:
- 브라우저에서 queued run 생성 후 상세 페이지가 polling으로 terminal 상태까지 전환된다.

### Step 4. 문서와 전체 회귀 검증

목적:
- async 계약 변경을 문서와 테스트에 반영하고 회귀를 닫는다.

파일:
- `README.md`
- `tests/unit/test_api_backtest_schema.py`
- `tests/integration/test_backtest_run_api_integration.py`
- `tests/integration/test_run_persistence_integration.py`
- `tests/integration/test_trade_analytics_api_integration.py`

구체 작업:
- README에 API backtest가 비동기라는 점과 run 조회 흐름을 추가한다.
- schema/contract 테스트를 새 상태와 nullable 필드 기준으로 갱신한다.
- touched area 통과 후 broader regression을 수행한다.

종료 조건:
- README와 테스트가 새 async contract를 설명하고, regression 명령이 모두 통과한다.

## Validation Matrix

### Required unit tests

- `pytest tests/unit/test_backtest_dispatcher.py -q`
- `pytest tests/unit/test_file_repository.py -q`
- `pytest tests/unit/test_supabase_repository.py -q`
- `pytest tests/unit/test_api_backtest_schema.py -q`

### Required integration tests

- `pytest tests/integration/test_backtest_run_api_integration.py -q`
- `pytest tests/integration/test_run_persistence_integration.py -q`
- `pytest tests/integration/test_trade_analytics_api_integration.py -q`

### Manual verification

- API에서 `POST /api/v1/backtests` 호출 시 즉시 `202`와 `queued` 응답 확인
- 같은 run이 `GET /api/v1/backtests/{run_id}`에서 `queued -> running -> succeeded|failed`로 전이하는지 확인
- 프론트엔드에서 새 run 생성 후 상세 페이지가 pending 상태를 거쳐 최종 상태로 바뀌는지 확인
- 서버 재시작 후 미완료 run이 `failed`와 interruption 메시지로 정리되는지 확인

## Recommended PR Slices

1. DTO/repository pending 상태 확장
2. dispatcher 도입 + async backtest route 전환
3. analytics/recovery/status semantics 정리
4. frontend pending UX 반영 + 문서/회귀

## Risks and Fallbacks

- worker thread와 repository 상태 전이가 꼬이면 run이 `running`에 고정될 수 있다.
대응:
- Step 1에서 dispatcher 단위 테스트를 먼저 추가하고, Step 2에서 startup recovery를 넣어 stranded state를 자동 정리한다.

- file repository의 nullable `finished_at` 처리 누락은 이전 run 조회 호환성을 깨뜨릴 수 있다.
대응:
- Step 0에서 기존 성공 run fixture와 pending run fixture를 모두 round-trip 테스트한다.

- frontend polling이 과도하면 불필요한 API 호출이 늘 수 있다.
대응:
- Step 3에서 active 상태에만 짧은 interval을 적용하고 terminal 상태에서는 polling을 중단한다.

- analytics route 상태 코드 변경으로 기존 클라이언트가 404만 기대할 수 있다.
대응:
- README와 frontend error handling을 같은 PR slice에서 갱신하고, 상세 페이지는 analytics를 success 상태에서만 호출한다.
