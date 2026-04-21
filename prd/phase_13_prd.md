# Phase 13 PRD

관련 문서:
- 이전 phase 범위/결과: `prd/phase_12_prd.md`
- 이전 phase 실행 검증: `prd/phase_12_task.md`
- 아키텍처 개요: `docs/architecture/overview.ko.md`
- 워크스페이스 분석: `docs/architecture/workspace-analysis.ko.md`
- 사용자 유즈케이스: `docs/architecture/user-use-cases.ko.md`
- 상세 구현 계획: `prd/phase_13_implementation_plan.md`
- 실행 추적: `prd/phase_13_task.md`

## 문서 목적

Phase 12까지의 구현으로 백테스트 실행, 라이브 preflight, API-owned runtime orchestration, 운영 콘솔 UI는 한 사이클로 연결되었다. 그러나 코드를 깊게 보면 제품으로서 가장 큰 다음 공백은 “운영 기록과 감사 가능성”이다. 현재 백테스트 run은 서버 저장소를 통해 보존되지만, 왜 그 run이 실행됐는지, 어떤 전략/설정으로 실행됐는지, 누가 실행했는지 같은 운영 메타데이터는 거의 남지 않는다. 라이브 runtime 역시 현재 상태와 마지막 preflight는 보이지만, 세션 이력과 운영 사건이 durable하게 남지 않는다.

이 문제는 문서에도 드러난다. `docs/architecture/workspace-analysis.ko.md`와 `docs/architecture/user-use-cases.ko.md`는 여전히 일부 과거 상태를 반영하고 있고, 현재 구현된 서버 저장소/API-owned runtime/dashboard console과 완전히 정렬되지 않는다. 즉, 시스템은 MVP를 넘어섰지만 운영 증적과 문서 진실 원천이 아직 분리되어 있다.

Phase 13의 목표는 이 간극을 메우는 것이다. 핵심 방향은 다음 세 가지다.

1. 백테스트와 라이브 운영의 **메타데이터와 상태 전이 기록**을 durable하게 남긴다.
2. API key 관리와 운영 제어에 **기본 거버넌스 필드**를 추가한다.
3. `docs/architecture/*`를 실제 코드 기준으로 다시 정렬해, 문서도 제품 운영의 진실 원천이 되게 만든다.

## Goal

1. 백테스트 run에 strategy/profile/provider/broker/request source 같은 운영 메타데이터를 1급 필드로 저장하고 조회하게 한다.
2. live runtime session의 시작/중지/실패/preflight 결과를 durable session history로 남긴다.
3. API key 관리에 `label`, `disabled`, `last_used_at` 같은 운영 필드를 추가해 기본 거버넌스를 확보한다.
4. `docs/architecture/overview.ko.md`, `workspace-analysis.ko.md`, `user-use-cases.ko.md`를 실제 구현과 맞게 업데이트한다.

이번 phase는 다음 원칙을 따른다.

- 기존 trading semantics는 바꾸지 않는다.
- 먼저 metadata와 lifecycle evidence를 추가하고, 복잡한 workflow engine은 도입하지 않는다.
- 파일 저장소와 Supabase 저장소 모두 같은 metadata contract를 지원해야 한다.
- 문서는 구현 이후 부속물이 아니라, 구현 상태를 설명하는 1급 산출물로 유지한다.

## Current Baseline

- `BacktestRunDTO`는 `run_id`, `status`, `started_at`, `finished_at`, `input_symbols`, `mode`, `result`, `error`만 가진다.
- `FileBacktestRunRepository`와 `SupabaseBacktestRunRepository`는 run 결과는 저장하지만 strategy/profile/provider/broker 같은 운영 메타데이터는 저장하지 않는다.
- 프런트엔드 `runsStore`는 여전히 `strategyProfile`과 `symbol` 일부를 로컬 저장소에 유지하며, 서버 저장소는 충분한 run context를 주지 못한다.
- `LiveRuntimeController`는 active session과 last preflight는 유지하지만, 종료된 세션 이력을 영속 저장하지 않는다.
- admin 키 관리 저장소는 `key_id`, `name`, `key`, `created_at`만 가지며, 비활성화나 last-used 갱신이 없다.
- `api/security.py`는 키 유효성만 검사하고, 어떤 키가 언제 사용됐는지 기록하지 않는다.
- `docs/architecture/workspace-analysis.ko.md`는 여전히 live orchestration, run persistence, dashboard 상태를 일부 과거 기준으로 설명하고 있다.
- `docs/architecture/user-use-cases.ko.md`도 백테스트 결과 저장 위치, run history, dashboard control 같은 부분이 현재 코드와 완전히 일치하지 않는다.

## Non-Goals

- 멀티테넌시 또는 고객별 워크스페이스 도입
- RBAC/SSO 같은 복잡한 인증 체계
- 대규모 이벤트 소싱 프레임워크 도입
- 실시간 브로커 체결/미체결 전용 store 추가
- 새로운 브로커/시장 지원
- 전략 탐색 실험관리 플랫폼 전체 도입

## Hard Decisions

### D-1. Run metadata는 `BacktestRunDTO`의 1급 필드로 승격한다

run 메타데이터를 프런트엔드 전용 store나 별도 sidecar 파일로 두지 않고, `BacktestRunDTO`와 저장소 스키마에 직접 추가한다. 그래야 list/detail API, analytics, 이후 promotion 흐름이 모두 같은 진실 원천을 공유할 수 있다.

### D-2. Live session history는 별도 session repository로 분리한다

백테스트 run 저장소와 라이브 세션 저장소는 lifecycle과 payload가 다르므로 같은 DTO에 억지로 넣지 않는다. `LiveRuntimeController`와 dashboard/event 흐름이 이미 별도이므로, session history도 별도 repository/DTO로 정의한다.

### D-3. API key 거버넌스는 최소 필드부터 추가한다

완전한 IAM을 도입하지 않고도 운영상 필요한 최소한의 필드는 분명하다. `label`, `disabled`, `last_used_at`를 추가하고, 인증 미들웨어가 성공 시점을 기반으로 last-used를 갱신하게 한다.

### D-4. Architecture docs는 이번 phase의 구현 범위에 포함한다

이번 phase는 문서 정합성이 제품 품질에 직접 영향을 주므로, `docs/architecture/*` 업데이트를 부가 작업이 아니라 필수 deliverable로 본다.

## Product Requirements

### PR-1. Durable backtest run metadata

- run 저장소는 `provider`, `broker`, `strategy_profile_id`, `pattern_set_id`, `requested_by`, `notes`, `source`를 저장할 수 있어야 한다.
- list API와 detail API는 이 메타데이터를 반환해야 한다.
- 프런트엔드 run list/detail은 서버 metadata를 우선 사용해야 한다.

### PR-2. Live session history

- live runtime start/stop/error/preflight 결과를 durable session history에 기록해야 한다.
- 운영자는 최소한 최근 세션 목록과 세션별 metadata를 조회할 수 있어야 한다.
- session history는 `session_id`, `started_at`, `ended_at`, `provider`, `broker`, `live_execution`, `symbols`, `last_state`, `last_error`, `preflight_summary`를 포함해야 한다.

### PR-3. API key governance basics

- admin API는 key의 `label`, `created_at`, `disabled`, `last_used_at`를 조회하게 해야 한다.
- disabled key는 인증에서 거절되어야 한다.
- 유효한 key로 요청이 처리되면 `last_used_at`가 갱신되어야 한다.

### PR-4. Architecture doc alignment

- `docs/architecture/overview.ko.md`, `workspace-analysis.ko.md`, `user-use-cases.ko.md`는 현재 코드 기준으로 다시 작성되어야 한다.
- 최소한 run persistence, dashboard console, runtime ownership, artifact 저장 위치, admin/API key 동작을 실제 구현과 일치시켜야 한다.

## Scope By Epic

### Epic A. Run metadata persistence

목표:
- 백테스트 실행 결과가 아니라 운영 맥락까지 함께 저장되게 만든다.

포함:
- DTO 확장
- file/supabase repository 스키마 확장
- API schema/list/detail 응답 확장
- 프런트엔드 run list/detail 연동

제외:
- 전략 promotion workflow 전체
- 실험 비교 대시보드

### Epic B. Live session history

목표:
- 라이브 세션 이력과 마지막 상태를 durable하게 남긴다.

포함:
- session DTO/repository
- controller start/stop/error hook
- session list/detail API
- dashboard 또는 run history와의 연결 entry point

제외:
- order-level durable store
- incident search UI 전체

### Epic C. API key governance + architecture docs

목표:
- 운영 접근 제어와 문서 정합성을 제품 수준으로 끌어올린다.

포함:
- admin repository/API 확장
- security middleware last-used update
- disabled key 거절
- architecture docs 업데이트

제외:
- RBAC/SSO
- 감사 내보내기(export) 기능

## Impacted Files

### Run/session domain and repositories
- `src/trading_system/backtest/dto.py`
- `src/trading_system/backtest/repository.py`
- `src/trading_system/backtest/file_repository.py`
- `src/trading_system/backtest/supabase_repository.py`
- `src/trading_system/app/live_runtime_controller.py`
- 신규 `src/trading_system/app/live_runtime_history.py` 또는 동등한 모듈

### API routes and schemas
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/routes/live_runtime.py`
- `src/trading_system/api/routes/admin.py`
- `src/trading_system/api/schemas.py`
- `src/trading_system/api/security.py`
- `src/trading_system/api/server.py`

### Frontend run/admin surfaces
- `frontend/app/runs/page.tsx`
- `frontend/app/runs/[runId]/page.tsx`
- `frontend/app/admin/page.tsx`
- `frontend/lib/api/backtests.ts`
- `frontend/lib/api/admin.ts`
- `frontend/lib/api/types.ts`
- `frontend/store/runsStore.ts`

### Validation and docs
- `tests/unit/test_file_repository.py`
- `tests/unit/test_supabase_repository.py`
- `tests/unit/test_live_runtime_controller.py`
- `tests/unit/test_api_security_helpers.py`
- `tests/unit/test_api_server.py`
- `tests/integration/test_run_persistence_integration.py`
- 신규 live session history 통합 테스트
- `docs/architecture/overview.ko.md`
- `docs/architecture/workspace-analysis.ko.md`
- `docs/architecture/user-use-cases.ko.md`

## Delivery Slices

### Slice 0. Backtest run metadata contract 확장
- run DTO/repository/API가 운영 메타데이터를 저장하고 반환하도록 확장한다.

### Slice 1. Live session history 추가
- live runtime controller가 durable session history를 기록하게 한다.

### Slice 2. Admin/API key governance 확장
- key disabled/last-used/label 필드를 추가하고 auth middleware를 갱신한다.

### Slice 3. Frontend와 architecture docs 정렬
- runs/admin 화면과 `docs/architecture/*`를 새 contract에 맞춰 정리한다.

## Success Metrics

- 백테스트 run list/detail에서 provider/broker/strategy profile 등 핵심 metadata를 조회할 수 있다.
- 최근 live session 이력이 서버 저장소에 남고 API로 조회 가능하다.
- disabled API key는 즉시 거절되고, active key는 `last_used_at`가 갱신된다.
- `docs/architecture/*`가 현재 코드와 충돌하지 않는 수준으로 정렬된다.
- file repo와 Supabase repo 모두 metadata 확장 테스트를 통과한다.

## Risks and Follow-up

- Supabase schema 확장은 migration과 하위 호환을 함께 고려해야 한다.
- live session history를 어디까지 dashboard에 노출할지 범위가 쉽게 커질 수 있으므로, 초기에는 list/detail API와 최소 UI 연결만 한다.
- API key `last_used_at` 갱신은 인증 hot path에 들어가므로 저장소 쓰기 비용이 커지지 않게 주의해야 한다.
- architecture docs 업데이트는 구현과 동시에 수행하지 않으면 다시 뒤처질 가능성이 높다.
