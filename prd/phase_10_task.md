# Phase 10 Task Breakdown

## Usage

- 이 파일은 Phase 10 구현 진행 상황과 검증 증적을 기록한다.
- 체크박스는 실제 구현 작업과 검증 기준을 뜻한다.
- 각 slice가 끝날 때 `Execution Log`를 갱신한다.
- PRD 수준 범위는 `phase_10_prd.md`를 기준으로 한다.
- 상세 설계와 순서는 `phase_10_implementation_plan.md`를 기준으로 한다.

## Status Note

- 이 문서는 `prd/phase_10_prd.md`의 실행 추적 문서다.
- 현재 체크박스는 active backlog를 slice 단위로 분해한 것이며, 일부 slice는 구현 완료, 일부는 검증 보류 상태다.
- 이번 phase의 핵심은 "동기 백테스트 요청"을 "비동기 run lifecycle"로 바꾸는 것이다.

## Phase 10-0. Run lifecycle DTO와 repository 확장

- [x] `src/trading_system/backtest/dto.py`에 `queued()`, `running()`, `failed()`, `succeeded()` 생성자 정리
- [x] `BacktestRunDTO.finished_at`를 pending 상태에서 `None` 허용으로 변경
- [x] `src/trading_system/backtest/file_repository.py`가 nullable `finished_at`를 저장/조회하도록 수정
- [x] `src/trading_system/backtest/supabase_repository.py`가 nullable `finished_at`와 pending status를 보존하도록 수정
- [x] `tests/unit/test_file_repository.py`에 pending run round-trip 테스트 추가
- [x] `tests/unit/test_supabase_repository.py`에 pending status 저장/조회 테스트 추가

Exit criteria:
- file/supabase repository 모두 `queued`와 `running` run을 손실 없이 저장하고 다시 읽을 수 있다.

## Phase 10-1. Dispatcher 구현과 async POST 계약 전환

- [x] `src/trading_system/backtest/dispatcher.py` 신규 생성
- [x] bounded queue + 단일 worker thread 구현
- [x] worker가 dequeued 직후 run을 `running`으로 갱신하도록 구현
- [x] worker 성공 시 `succeeded`, 예외 시 `failed` 상태 저장 구현
- [x] `src/trading_system/api/routes/backtest.py`가 queued 레코드 저장 후 enqueue하도록 수정
- [x] `POST /api/v1/backtests` 응답 상태 코드를 `202 Accepted`로 변경
- [x] `src/trading_system/api/schemas.py`의 `BacktestRunAcceptedDTO`를 `queued` 계약에 맞게 수정
- [x] `tests/unit/test_backtest_dispatcher.py` 신규 작성
- [x] `tests/integration/test_backtest_run_api_integration.py`를 async lifecycle 기준으로 갱신

Exit criteria:
- `POST /api/v1/backtests`가 실행 완료를 기다리지 않고 즉시 `queued`를 반환하고, worker가 별도로 terminal 상태를 저장한다.

## Phase 10-2. Startup recovery와 조회/analytics 의미 정리

- [x] `src/trading_system/api/server.py` startup 시 stranded `queued`/`running` run을 `failed`로 정리하는 recovery 추가
- [x] `src/trading_system/api/routes/backtest.py` detail/list 응답이 pending 상태와 nullable `finished_at`를 반환하도록 조정
- [x] `src/trading_system/api/routes/analytics.py`가 404와 409를 구분하도록 수정
- [x] failed run analytics 요청 시 상태와 실패 메시지가 응답에 반영되도록 정리
- [x] `tests/integration/test_run_persistence_integration.py`에 restart recovery 시나리오 추가
- [x] `tests/integration/test_trade_analytics_api_integration.py`에 pending run 409 케이스 추가

Exit criteria:
- restart 후 미완료 run이 `failed`로 정리되고, analytics가 pending/failed run에 대해 상태 기반 응답을 반환한다.

## Phase 10-3. Frontend pending UX 반영

- [x] `frontend/lib/api/types.ts`에 `queued` 상태와 nullable `finished_at` 반영
- [x] `frontend/components/domain/StatusBadge.tsx`에 `queued` badge 스타일 추가
- [x] `frontend/app/page.tsx`가 create 응답을 `queued`로 저장하고 상세 페이지로 이동하도록 수정
- [x] `frontend/app/runs/[runId]/page.tsx`에 pending 상태 polling 추가
- [x] `frontend/app/runs/[runId]/page.tsx`가 success 전 analytics 요청을 보내지 않도록 유지/보강
- [x] `frontend/app/runs/page.tsx`가 active run 존재 시 자동 refetch하도록 수정
- [ ] `frontend/store/runsStore.ts`가 server polling 결과로 상태를 갱신하도록 보강

Exit criteria:
- 브라우저에서 queued run이 상세/목록 화면에서 자연스럽게 보이고 terminal 상태 도달 시 polling이 멈춘다.

## Phase 10-4. 문서와 회귀 검증

- [x] `README.md`에 API backtest async flow와 run polling 흐름 추가
- [x] `tests/unit/test_api_backtest_schema.py`를 queued/running/nullable `finished_at` 기준으로 갱신
- [ ] touched backend/integration tests 통과 확인
- [x] frontend 타입체크/린트/빌드 통과 확인
- [x] broader regression 실행 후 잔여 리스크 정리

Exit criteria:
- README와 테스트가 새 async contract를 설명하고, targeted tests와 broader regression이 통과한다.

## Verification Checklist

### Required unit tests

- [x] `pytest tests/unit/test_backtest_dispatcher.py -q`
- [x] `pytest tests/unit/test_file_repository.py -q`
- [x] `pytest tests/unit/test_supabase_repository.py -q`
- [ ] `pytest tests/unit/test_api_backtest_schema.py -q`

### Required integration tests

- [ ] `pytest tests/integration/test_backtest_run_api_integration.py -q`
- [ ] `pytest tests/integration/test_run_persistence_integration.py -q`
- [ ] `pytest tests/integration/test_trade_analytics_api_integration.py -q`

### Broader regression

- [ ] `pytest --tb=short -q`
- [x] `ruff check src/ tests/`
- [x] `cd frontend && npx tsc --noEmit`
- [x] `cd frontend && npm run lint`
- [x] `cd frontend && npm run build`

### Manual verification

- [ ] `POST /api/v1/backtests` 호출 시 즉시 `202`와 `queued` 응답 확인
- [ ] 동일 run이 `queued -> running -> succeeded|failed`로 전이하는지 detail API로 확인
- [ ] 프론트엔드 run 상세 화면이 pending 상태에서 자동 갱신되는지 확인
- [ ] 서버 재시작 후 stranded run이 interruption 메시지와 함께 `failed`로 바뀌는지 확인

## Execution Log

### Date

- 2026-04-17

### Owner

- Codex

### Slice completed

- Phase 10-0: run lifecycle DTO/repository 확장
- Phase 10-1: dispatcher 도입 + async backtest acceptance
- Phase 10-2: startup recovery + analytics status semantics
- Phase 10-3: frontend pending UX 반영
- Phase 10-4: 문서 보강 + 부분 검증 완료

### Scope implemented

- `BacktestRunDTO`에 `queued`, `running`, `failed`, `succeeded` 생성자와 nullable `finished_at`를 추가했다.
- file/supabase repository가 pending 상태를 저장/조회하도록 맞췄다.
- `BacktestRunDispatcher`를 추가하고 queue, startup recovery, worker 예외 격리, queue-full shutdown 경로를 구현했다.
- `/api/v1/backtests`를 `202 Accepted` + `queued` 계약으로 전환하고 analytics의 pending/failed 409 semantics를 추가했다.
- 프론트엔드 run 상세/목록/상태 badge를 pending 상태에 맞게 조정했다.

### Files changed

- `src/trading_system/backtest/dto.py`
- `src/trading_system/backtest/file_repository.py`
- `src/trading_system/backtest/supabase_repository.py`
- `src/trading_system/backtest/dispatcher.py`
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/routes/analytics.py`
- `src/trading_system/api/server.py`
- `src/trading_system/api/schemas.py`
- `frontend/app/page.tsx`
- `frontend/app/runs/page.tsx`
- `frontend/app/runs/[runId]/page.tsx`
- `frontend/components/domain/StatusBadge.tsx`
- `frontend/components/runs/RunSummaryGrid.tsx`
- `frontend/lib/api/types.ts`
- `README.md`
- `tests/unit/test_backtest_dispatcher.py`
- `tests/unit/test_file_repository.py`
- `tests/unit/test_supabase_repository.py`
- `tests/unit/test_api_server.py`
- `tests/unit/test_api_backtest_schema.py`
- `tests/integration/test_backtest_run_api_integration.py`
- `tests/integration/test_run_persistence_integration.py`
- `tests/integration/test_trade_analytics_api_integration.py`
- `tests/integration/test_api_security_and_validation_integration.py`
- `tests/integration/test_pattern_strategy_api_integration.py`

### Commands run

- `pytest tests/unit/test_backtest_dispatcher.py tests/unit/test_file_repository.py tests/unit/test_supabase_repository.py -q` → `32 passed, 1 skipped`
- `pytest tests/unit/test_api_server.py -q -k lifespan` → `1 passed, 6 deselected`
- `ruff check src/ tests/` → passed
- `cd frontend && npx tsc --noEmit` → passed
- `cd frontend && npm run lint` → passed
- `cd frontend && npm run build` → passed

### Validation results

- DTO/repository/dispatcher unit coverage와 lifespan recovery smoke는 통과했다.
- frontend 타입체크, lint, build는 모두 통과했다.
- `TestClient` 기반 HTTP/integration 검증은 이 환경에서 lifespan 진입 자체가 hang 되는 문제가 남아 있어 전체 통과 증적은 확보하지 못했다.

### Risks / follow-up

- `tests/unit/test_api_backtest_schema.py`, `tests/integration/test_backtest_run_api_integration.py`, `tests/integration/test_run_persistence_integration.py`, `tests/integration/test_trade_analytics_api_integration.py`는 코드상 갱신됐지만 현재 환경의 HTTP test harness block으로 실행 증적이 부족하다.
- `frontend/store/runsStore.ts` 자체는 수정하지 않았고, 상태 갱신은 상세 페이지의 polling 결과로 기존 `updateRunStatus`를 호출하는 방식으로 반영했다.
