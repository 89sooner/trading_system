# Phase 13 Implementation Plan

## Goal

Phase 13의 구현 목표는 운영자용 제품 표면 뒤에 있는 기록 계층을 강화하는 것이다. 구체적으로는 backtest run metadata를 1급화하고, live session history를 durable하게 남기며, API key governance 기본 필드를 추가하고, architecture docs를 현재 코드 기준으로 다시 정렬하는 것이다.

핵심 구현 원칙:

1. 결과 데이터보다 운영 맥락(metadata)을 우선 보강한다.
2. file repo와 Supabase repo가 같은 contract를 구현해야 한다.
3. live runtime history는 backtest run history와 분리된 별도 저장소로 설계한다.
4. auth hot path 변경은 최소한으로 하고, disabled/last-used 기본 기능만 넣는다.
5. 문서 업데이트는 구현 이후가 아니라 구현 범위의 일부로 같이 수행한다.

## Preconditions

- Phase 12의 runtime console과 structured preflight contract는 현재 baseline으로 본다.
- `BacktestRunDTO`/repository/API가 이미 서버 저장소를 중심으로 동작하므로, metadata 확장은 기존 contract를 깨지 않는 방향으로 진행해야 한다.
- 프런트엔드 `runsStore`는 fallback 용도로만 남기고, 장기적으로는 서버 metadata가 primary source가 되어야 한다.
- `docs/architecture/*`는 일부 내용이 현재 코드보다 뒤처져 있으므로, 이번 phase에서 적극적으로 갱신해야 한다.

## Locked Design Decisions

### 1. Backtest metadata는 run DTO와 저장소에 직접 추가한다

- 별도 metadata side-table이나 프런트 저장소 보강이 아니라, `BacktestRunDTO`/repository/API response를 직접 확장한다.
- 최소 필드는 `provider`, `broker`, `strategy_profile_id`, `pattern_set_id`, `source`, `requested_by`, `notes`로 고정한다.

### 2. Live session history는 별도 저장소/DTO로 분리한다

- live session lifecycle은 backtest run과 다르므로 별도 `LiveRuntimeSessionRecord` 계열 DTO/repository를 만든다.
- 초기 단계에서는 최근 세션 list/detail과 controller hook만 지원한다.

### 3. API key governance는 저장소 필드와 middleware hook으로 해결한다

- admin repository가 `label`, `disabled`, `last_used_at`를 저장한다.
- security middleware는 인증 성공 시 repo에 `last_used_at`를 기록한다.
- disabled key는 env key와 구분되는 repository-managed key 경로에서 즉시 차단한다.

### 4. Architecture docs는 코드 상태를 기준으로 재작성한다

- `overview.ko`, `workspace-analysis.ko`, `user-use-cases.ko` 모두 현재 저장소 동작을 기준으로 업데이트한다.
- 과거 phase 문구를 덧붙이는 방식보다, 현재 상태를 직접 설명하는 서술로 바꾼다.

## Contract Deltas

## A. Backtest run metadata contract

대상:
- `src/trading_system/backtest/dto.py`
- `src/trading_system/backtest/repository.py`
- `src/trading_system/backtest/file_repository.py`
- `src/trading_system/backtest/supabase_repository.py`
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/schemas.py`

필수 변화:
- run DTO와 API DTO에 metadata 필드 추가
- queue/running/succeeded/failed factory가 metadata를 함께 받게 확장
- file/supabase 저장소 모두 metadata persistence 지원
- list/detail API가 metadata를 반환

비고:
- 기존 필드와 응답 shape는 유지하고 metadata를 additive하게 추가

## B. Live session history contract

대상:
- 신규 live session history DTO/repository 모듈
- `src/trading_system/app/live_runtime_controller.py`
- `src/trading_system/api/routes/live_runtime.py`
- `src/trading_system/api/schemas.py`
- 필요 시 `src/trading_system/api/server.py`

필수 변화:
- session start/stop/error/preflight 결과를 저장하는 history contract 추가
- controller가 lifecycle hook마다 session record를 저장
- recent session list/detail API 추가

비고:
- UI는 최소 연결만 하고, 전체 history dashboard는 후속 phase로 미룸

## C. API key governance + docs contract

대상:
- `src/trading_system/api/admin/repository.py`
- `src/trading_system/api/routes/admin.py`
- `src/trading_system/api/security.py`
- `frontend/app/admin/page.tsx`
- `frontend/lib/api/admin.ts`
- `frontend/lib/api/types.ts`
- `docs/architecture/overview.ko.md`
- `docs/architecture/workspace-analysis.ko.md`
- `docs/architecture/user-use-cases.ko.md`

필수 변화:
- key list/create/delete API가 governance 필드를 읽고 쓸 수 있게 확장
- middleware가 last-used 갱신과 disabled key 거절 지원
- admin UI가 새 필드를 표시
- architecture docs가 현재 구현과 일치하도록 업데이트

비고:
- 환경변수 기반 static key는 metadata/disable 대상에서 제외

## Sequenced Implementation

### Step 0. Backtest run metadata 확장

목적:
- 서버 저장소와 API가 run context를 함께 보존하게 만든다.

파일:
- `src/trading_system/backtest/dto.py`
- `src/trading_system/backtest/repository.py`
- `src/trading_system/backtest/file_repository.py`
- `src/trading_system/backtest/supabase_repository.py`
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/schemas.py`
- `frontend/lib/api/types.ts`

구체 작업:
- metadata 필드 정의 및 factory 메서드 확장
- file/supabase 저장소 serialize/deserialize 확장
- backtest create/list/detail API와 프런트 타입 동기화

종료 조건:
- run list/detail 응답에서 metadata를 안정적으로 조회할 수 있다.

### Step 1. Live session history 저장소 도입

목적:
- live runtime lifecycle을 종료 후에도 설명 가능한 기록으로 남긴다.

파일:
- 신규 live session history 모듈
- `src/trading_system/app/live_runtime_controller.py`
- `src/trading_system/api/routes/live_runtime.py`
- `src/trading_system/api/schemas.py`
- `src/trading_system/api/server.py`

구체 작업:
- session record DTO/repository 정의
- controller start/stop/error/preflight hook 저장
- session list/detail API 추가

종료 조건:
- 최근 live session 이력이 durable store에서 조회된다.

### Step 2. API key governance 기본 필드 추가

목적:
- 운영 접근 제어에 최소한의 lifecycle 정보를 붙인다.

파일:
- `src/trading_system/api/admin/repository.py`
- `src/trading_system/api/routes/admin.py`
- `src/trading_system/api/security.py`
- `frontend/app/admin/page.tsx`
- `frontend/lib/api/admin.ts`
- `frontend/lib/api/types.ts`

구체 작업:
- `label`, `disabled`, `last_used_at` 필드 추가
- admin API shape와 UI 갱신
- security middleware 성공 인증 시 last-used 기록
- disabled key 거절 처리

종료 조건:
- repository-managed key는 disable/usage tracking이 가능하다.

### Step 3. Frontend run/admin surfaces + architecture docs 정렬

목적:
- 새 contract를 운영 화면과 architecture docs에 반영한다.

파일:
- `frontend/app/runs/page.tsx`
- `frontend/app/runs/[runId]/page.tsx`
- `frontend/app/admin/page.tsx`
- `frontend/store/runsStore.ts`
- `docs/architecture/overview.ko.md`
- `docs/architecture/workspace-analysis.ko.md`
- `docs/architecture/user-use-cases.ko.md`

구체 작업:
- run list/detail이 서버 metadata를 우선 노출
- admin 화면이 governance 필드 표시
- runsStore fallback 의존 축소
- architecture docs 현재 상태 반영

종료 조건:
- UI와 docs가 새 metadata/history/governance contract를 설명하고 소비한다.

## Validation Matrix

### Required unit tests
- `pytest tests/unit/test_file_repository.py -q`
- `pytest tests/unit/test_supabase_repository.py -q`
- `pytest tests/unit/test_live_runtime_controller.py -q`
- `pytest tests/unit/test_api_security_helpers.py -q`

### Required integration tests
- `pytest tests/integration/test_run_persistence_integration.py -q`
- 신규 live session history API integration test
- admin key governance integration test

### Manual verification
- 백테스트 실행 후 run list/detail에서 metadata 노출 확인
- live runtime start/stop 후 session history 조회 확인
- disabled key로 API 호출 시 401 또는 동등한 거절 확인
- admin UI에서 last_used_at 표시 확인
- architecture docs와 실제 UI/API 경로 대조 확인

## Recommended PR Slices

1. Backtest metadata DTO/repository/API 확장
2. Live session history repository + controller hook + API
3. API key governance + admin UI
4. Run/admin UI 정렬 + architecture docs 업데이트

## Risks and Fallbacks

- Supabase migration 범위가 커질 수 있다.

대응:
- Step 0과 Step 1에서 additive schema migration만 수행하고, 기존 컬럼/응답은 유지한다.

- security middleware에서 저장소 쓰기 실패가 auth hot path를 불안정하게 만들 수 있다.

대응:
- last-used update는 best-effort로 처리하고, 인증 자체는 실패시키지 않는 방향을 기본으로 한다.

- live session history UI 범위가 쉽게 확장될 수 있다.

대응:
- 이번 phase에서는 list/detail API와 최소 진입점만 넣고, 전용 history 화면은 후속 phase로 분리한다.
