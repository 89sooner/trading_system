# Phase 12 Implementation Plan

## Goal

Phase 12의 구현 목표는 live runtime orchestration 위에 운영자용 제품 표면을 덧씌우는 것이다. 구체적으로는 structured preflight 계약을 만들고, controller와 dashboard가 그 문맥을 보존하며, launch flow를 preflight-first 운영 콘솔로 재구성하는 것이다.

핵심 구현 원칙:

1. 거래 semantics보다 운영 semantics를 강화한다.
2. 기존 live preflight endpoint를 확장해 backward compatibility를 유지한다.
3. controller는 마지막 preflight snapshot을 단일 진실 원천으로 가진다.
4. launch form은 fresh preflight가 없으면 start를 막는다.
5. guarded live는 UI와 백엔드에서 모두 명시적 guard를 유지한다.

## Preconditions

- Phase 11의 API-owned runtime controller는 현재 baseline으로 본다.
- `LiveTradingLoop`와 KIS guard는 이미 동작하므로 이번 phase에서 trading logic 변경은 하지 않는다.
- dashboard는 기존 polling/SSE 구조를 유지하되, operator decision surface를 강화하는 방향만 허용한다.
- task 문서는 실제 수행된 작업과 검증 증적을 회고형으로 남긴다.

## Locked Design Decisions

### 1. Preflight는 기존 route에서 확장한다

- `/api/v1/live/preflight`를 유지하면서 richer readiness 필드를 추가한다.
- start route도 같은 preflight 결과를 응답에 포함해, operator가 실제 launch에 사용된 snapshot을 확인할 수 있게 한다.

### 2. Controller가 last preflight를 저장한다

- `LiveRuntimeController`에 `record_preflight()`를 추가한다.
- explicit preflight와 runtime start 둘 다 이 메서드를 호출한다.
- dashboard status는 controller snapshot을 통해 last preflight를 읽는다.

### 3. Dashboard status는 “loop state + controller context”를 같이 반환한다

- active 여부, controller state detail, broker, stop_supported, latest_incident, last_preflight를 함께 반환한다.
- loop가 없어도 `status`는 `200`으로 operator context를 유지한다.

### 4. Launch form은 preflight 결과 freshness를 signature로 판단한다

- 현재 symbols/provider/broker/live_execution payload를 문자열 signature로 계산한다.
- 마지막 preflight signature와 다르면 stale로 간주하고 start를 막는다.

## Contract Deltas

## A. Preflight/readiness contract

대상:
- `src/trading_system/app/services.py`
- `src/trading_system/api/schemas.py`
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/routes/live_runtime.py`

필수 변화:
- `PreflightCheckResult`에 `blocking_reasons`, `warnings`, `checks`, `symbol_checks`, `next_allowed_actions`, `checked_at` 추가
- `LivePreflightResponseDTO`와 `LiveRuntimeStartResponseDTO`에 대응 필드 추가
- preflight route/start route가 동일한 변환 함수를 재사용

비고:
- `quote_summary`, `quote_summaries`, `symbol_count`는 하위 호환을 위해 유지

## B. Controller and dashboard status contract

대상:
- `src/trading_system/app/live_runtime_controller.py`
- `src/trading_system/api/routes/dashboard.py`
- `src/trading_system/api/schemas.py`

필수 변화:
- controller snapshot에 `stop_supported`, `last_preflight` 추가
- dashboard status에 `controller_state_detail`, `active`, `broker`, `last_preflight`, `latest_incident` 추가
- loop가 없는 상태에서도 status route는 controller snapshot을 반환

비고:
- incident는 in-memory recent event scan으로 계산

## C. Frontend operations console contract

대상:
- `frontend/components/dashboard/RuntimeLaunchForm.tsx`
- `frontend/app/dashboard/page.tsx`
- `frontend/components/dashboard/DashboardMetrics.tsx`
- `frontend/hooks/useDashboardPolling.ts`
- `frontend/lib/api/dashboard.ts`
- `frontend/lib/api/types.ts`

필수 변화:
- preflight API client 추가
- launch form이 preflight 결과를 렌더링하고 stale 상태를 감지
- guarded live confirmation dialog 추가
- dashboard page가 runtime briefing / last preflight / latest incident 카드를 포함

비고:
- 기존 polling/SSE mechanics는 유지

## Sequenced Implementation

### Step 0. Structured preflight result 모델 확장

목적:
- 백엔드에서 operator-facing readiness contract를 만들고 API DTO까지 연결한다.

파일:
- `src/trading_system/app/services.py`
- `src/trading_system/api/schemas.py`
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/routes/live_runtime.py`

구체 작업:
- `ReadinessCheck`, `SymbolReadiness` 모델 추가
- generic live path와 KIS path 모두 `PreflightCheckResult` 확장
- preflight 결과를 API DTO로 변환하는 helper 추가
- start route가 launch에 사용된 preflight snapshot을 응답에 포함

종료 조건:
- preflight 응답과 start 응답 모두 structured readiness 필드를 포함한다.

### Step 1. Controller와 dashboard status 문맥 확장

목적:
- 마지막 preflight와 최근 incident를 controller/status에서 지속적으로 보여준다.

파일:
- `src/trading_system/app/live_runtime_controller.py`
- `src/trading_system/api/routes/dashboard.py`
- `src/trading_system/api/schemas.py`

구체 작업:
- controller에 last preflight snapshot 저장
- status route에 active/controller detail/broker/stop_supported 추가
- latest incident 계산 helper 추가
- loop 부재 시에도 status `200` 응답 유지

종료 조건:
- active loop가 없어도 status API가 controller/preflight 문맥을 반환한다.

### Step 2. Launch form과 dashboard 운영 콘솔 구현

목적:
- operator가 preflight-first 흐름으로 launch하고, 같은 화면에서 상태를 읽을 수 있게 한다.

파일:
- `frontend/components/dashboard/RuntimeLaunchForm.tsx`
- `frontend/app/dashboard/page.tsx`
- `frontend/components/dashboard/DashboardMetrics.tsx`
- `frontend/hooks/useDashboardPolling.ts`
- `frontend/lib/api/dashboard.ts`
- `frontend/lib/api/types.ts`

구체 작업:
- launch payload signature 기반 freshness 판단
- blocking reasons / warnings / checks / symbol checks 렌더링
- guarded live confirmation dialog 추가
- dashboard cards 재구성

종료 조건:
- operator가 dashboard에서 preflight를 먼저 확인한 뒤에만 start를 진행할 수 있다.

### Step 3. 문서와 검증 기록 정리

목적:
- 이번 phase 범위와 검증 결과를 repository docs와 PRD에 남긴다.

파일:
- `README.md`
- `docs/runbooks/deploy-production.md`
- `docs/runbooks/deploy-production.ko.md`
- `prd/phase_12_prd.md`
- `prd/phase_12_task.md`

구체 작업:
- README에 enriched preflight/start semantics 반영
- deploy runbook에 preflight-first 운영 절차 반영
- task 문서에 실제 실행 명령과 한계 기록

종료 조건:
- operator-facing docs와 phase 기록이 실제 구현 상태와 일치한다.

## Validation Matrix

### Required unit tests
- `pytest tests/unit/test_app_services.py -q`
- `pytest tests/unit/test_live_runtime_controller.py -q`
- `pytest tests/unit/test_live_runtime_routes.py -q`

### Required integration tests
- `pytest tests/integration/test_kis_preflight_integration.py -q`
- `pytest tests/integration/test_live_runtime_api_integration.py -q`

### Manual verification
- dashboard에서 preflight 결과가 blocking/warning/check 단위로 보이는지 확인
- preflight 이후 설정 변경 시 start가 비활성화되는지 확인
- guarded live 선택 시 confirmation dialog가 뜨는지 확인
- status 화면에서 last preflight와 latest incident가 보이는지 확인

## Recommended PR Slices

1. Preflight result model + API DTO 확장
2. Controller snapshot + dashboard status enrichment
3. Launch form / dashboard UX 재구성
4. Docs + PRD 기록 정리

## Risks and Fallbacks

- `TestClient(create_app())` 경로는 환경에 따라 startup 정체가 발생할 수 있다.

대응:
- 이번 phase에서는 route/service/controller 테스트를 우선 실행하고, task 문서에 미완료 검증으로 남긴다.

- launch form이 너무 많은 상태를 한 번에 보여주면 operator가 오히려 혼란스러울 수 있다.

대응:
- blocking reasons, warnings, next allowed actions를 우선 정보로 두고, checks/symbol checks는 보조 설명으로 배치한다.

- latest incident는 최근 이벤트 버퍼 의존이라, loop 재시작 후 문맥이 사라질 수 있다.

대응:
- 이번 phase에서는 in-memory contract만 정리하고, durable incident history는 후속 phase로 분리한다.
