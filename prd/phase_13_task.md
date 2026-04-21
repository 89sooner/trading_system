# Phase 13 Task Breakdown

## Usage

- 이 파일은 Phase 13 구현 진행 상황과 검증 증적을 기록한다.
- 체크박스는 실제 구현 작업과 검증 기준을 뜻한다.
- 각 slice가 끝날 때 `Execution Log`를 갱신한다.
- PRD 수준 범위는 `phase_13_prd.md`를 기준으로 한다.
- 상세 설계와 순서는 `phase_13_implementation_plan.md`를 기준으로 한다.

## Status Note

- 이 문서는 `prd/phase_13_prd.md`의 실행 추적 문서다.
- 현재 체크박스는 이번 구현에서 실제 완료한 범위와 남은 검증 리스크를 함께 반영한다.
- 이번 phase의 핵심은 운영 기록(metadata/session history)과 거버넌스, architecture docs 정합성을 강화하는 것이다.

## Phase 13-0. Backtest run metadata 확장

- [x] `src/trading_system/backtest/dto.py`에 run metadata 필드 추가
- [x] run queued/running/succeeded/failed factory가 metadata를 함께 받도록 확장
- [x] `src/trading_system/backtest/file_repository.py` serialize/deserialize 확장
- [x] `src/trading_system/backtest/supabase_repository.py` metadata persistence 확장
- [x] `src/trading_system/api/routes/backtest.py` list/detail/create 응답에 metadata 연결
- [x] `src/trading_system/api/schemas.py`와 `frontend/lib/api/types.ts`를 새 필드와 동기화

Exit criteria:
- backtest run list/detail API가 provider/broker/strategy profile 등 metadata를 반환한다.

## Phase 13-1. Live session history 저장소 도입

- [x] live session record DTO 정의
- [x] live session history repository(file 또는 existing repo pattern 재사용) 추가
- [x] `LiveRuntimeController`가 start/stop/error/preflight lifecycle을 history에 기록
- [x] 최근 session list/detail API 추가
- [x] session history 관련 unit/integration 테스트 추가

Exit criteria:
- live runtime session 이력이 durable하게 저장되고 API로 조회 가능하다.

## Phase 13-2. API key governance 기본 필드 추가

- [x] `src/trading_system/api/admin/repository.py`에 `label`, `disabled`, `last_used_at` 필드 추가
- [x] admin list/create/delete API를 새 contract에 맞게 확장
- [x] `src/trading_system/api/security.py`에서 성공 인증 시 `last_used_at` 갱신
- [x] disabled key 거절 처리
- [x] `frontend/app/admin/page.tsx`와 API 타입/client를 새 필드에 맞게 갱신

Exit criteria:
- repository-managed key는 disable/usage tracking이 가능하고 UI에서 확인된다.

## Phase 13-3. Run/admin UI와 architecture docs 정렬

- [x] `frontend/app/runs/page.tsx`가 서버 metadata를 표시하도록 확장
- [x] `frontend/app/runs/[runId]/page.tsx`가 strategy/provider/broker/source metadata를 표시
- [x] `frontend/store/runsStore.ts` fallback 역할만 남기도록 정리
- [x] `docs/architecture/overview.ko.md`를 현재 코드 기준으로 업데이트
- [x] `docs/architecture/workspace-analysis.ko.md`를 현재 상태로 재작성
- [x] `docs/architecture/user-use-cases.ko.md`의 저장 위치/운영 흐름을 현재 구현과 맞춤

Exit criteria:
- UI와 architecture docs가 현재 저장소의 실제 동작을 설명한다.

## Verification Checklist

### Required unit tests

- [x] `pytest tests/unit/test_file_repository.py -q`
- [x] `pytest tests/unit/test_supabase_repository.py -q`
- [x] `pytest tests/unit/test_live_runtime_controller.py -q`
- [x] `pytest tests/unit/test_api_security_helpers.py -q`

### Required integration tests

- [ ] `pytest tests/integration/test_run_persistence_integration.py -q`
- [x] live session history integration test 추가 및 실행
- [ ] admin key governance integration test 추가 및 실행

### Broader regression

- [x] `ruff check` touched 범위 실행
- [ ] `pytest --tb=short -q`
- [x] `cd frontend && npm run lint`
- [x] `cd frontend && npm run build`

### Manual verification

- [ ] backtest 실행 후 run list/detail metadata 표시 확인
- [ ] live session start/stop 후 recent session history 확인
- [ ] disabled key 거절 및 last-used 갱신 확인
- [ ] architecture docs 문구가 실제 API/UI 동작과 충돌하지 않는지 확인

## Execution Log

### Date
- 2026-04-19

### Owner
- Codex

### Slice completed
- Phase 13-0: backtest run metadata contract 확장
- Phase 13-1: live session history 저장소 + API 추가
- Phase 13-2: API key governance 기본 필드 추가
- Phase 13-3: runs/admin UI와 architecture docs 정렬

### Scope implemented
- `BacktestRunDTO`와 file/Supabase 저장소에 run metadata를 추가하고, backtest list/detail/create API가 이를 반환하도록 확장했다.
- `LiveRuntimeController`에 durable session history 저장소를 연결하고, live runtime session list/detail API를 추가했다.
- admin key 저장소와 API를 `label`, `disabled`, `last_used_at` 기준으로 확장하고, security middleware가 repository-managed key 사용 시점을 기록하도록 바꿨다.
- `runs/admin` 화면과 `docs/architecture/*.md`, `docs/architecture/*.ko.md`를 새 metadata/governance/session history 상태에 맞게 정렬했다.

### Files changed
- `src/trading_system/backtest/dto.py`
- `src/trading_system/backtest/dispatcher.py`
- `src/trading_system/backtest/file_repository.py`
- `src/trading_system/backtest/supabase_repository.py`
- `src/trading_system/app/live_runtime_controller.py`
- `src/trading_system/app/live_runtime_history.py`
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/routes/live_runtime.py`
- `src/trading_system/api/routes/admin.py`
- `src/trading_system/api/security.py`
- `src/trading_system/api/server.py`
- `src/trading_system/api/admin/repository.py`
- `src/trading_system/api/schemas.py`
- `frontend/app/page.tsx`
- `frontend/app/runs/page.tsx`
- `frontend/app/runs/[runId]/page.tsx`
- `frontend/app/admin/page.tsx`
- `frontend/lib/api/admin.ts`
- `frontend/lib/api/types.ts`
- `frontend/store/runsStore.ts`
- `scripts/migrations/003_add_backtest_metadata_and_live_runtime_sessions.sql`
- `docs/architecture/overview.md`
- `docs/architecture/overview.ko.md`
- `docs/architecture/workspace-analysis.md`
- `docs/architecture/workspace-analysis.ko.md`
- `docs/architecture/user-use-cases.md`
- `docs/architecture/user-use-cases.ko.md`
- `docs/runbooks/deploy-production.md`
- `docs/runbooks/deploy-production.ko.md`
- `tests/unit/test_file_repository.py`
- `tests/unit/test_supabase_repository.py`
- `tests/unit/test_live_runtime_controller.py`
- `tests/unit/test_live_runtime_history.py`
- `tests/unit/test_api_key_repository.py`
- `tests/integration/test_live_runtime_api_integration.py`
- `tests/integration/test_run_persistence_integration.py`

### Commands run
- `ruff check src/trading_system/backtest/dto.py src/trading_system/backtest/dispatcher.py src/trading_system/backtest/file_repository.py src/trading_system/backtest/supabase_repository.py src/trading_system/app/live_runtime_controller.py src/trading_system/app/live_runtime_history.py src/trading_system/api/routes/backtest.py src/trading_system/api/routes/live_runtime.py src/trading_system/api/routes/admin.py src/trading_system/api/security.py src/trading_system/api/server.py src/trading_system/api/admin/repository.py src/trading_system/api/schemas.py tests/unit/test_file_repository.py tests/unit/test_supabase_repository.py tests/unit/test_live_runtime_controller.py tests/unit/test_live_runtime_history.py tests/unit/test_api_key_repository.py tests/integration/test_live_runtime_api_integration.py`
- `UV_CACHE_DIR=.uv-cache uv run --python .venv/bin/python --no-sync pytest tests/unit/test_file_repository.py tests/unit/test_supabase_repository.py tests/unit/test_live_runtime_controller.py tests/unit/test_live_runtime_history.py tests/unit/test_api_key_repository.py tests/integration/test_live_runtime_api_integration.py -q` → `44 passed, 1 skipped`
- `UV_CACHE_DIR=.uv-cache uv run --python .venv/bin/python --no-sync pytest tests/unit/test_api_security_helpers.py -q` → `3 passed`
- `cd frontend && npm run lint` → passed
- `cd frontend && npm run build` → passed
- `UV_CACHE_DIR=.uv-cache uv run --python .venv/bin/python --no-sync pytest tests/integration/test_run_persistence_integration.py::test_run_detail_persists_across_repository_recreation -q` → 환경에서 완료 결과 미회수

### Validation results
- touched backend/store/API/history 범위의 lint는 통과했다.
- file repository, supabase repository(mocked), live runtime controller, live runtime history, api key repository, live runtime API 직접 검증은 통과했다.
- frontend lint/build는 통과했다.
- `run_persistence_integration`은 여전히 이 환경에서 `TestClient(create_app())` 경로가 정체되어 완료 증적을 확보하지 못했다.

### Risks / follow-up
- `tests/integration/test_run_persistence_integration.py`는 환경 의존 정체 이슈가 여전히 남아 있다.
- admin key governance는 repository-managed key에만 적용되며, env 기반 static key는 disable/last-used 대상이 아니다.
- live session history는 API로 조회 가능하지만, 전용 브라우저 history 화면은 아직 없다.
