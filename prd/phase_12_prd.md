# Phase 12 PRD

관련 문서:
- 이전 phase 범위/결과: `prd/phase_11_prd.md`
- 이전 phase 실행 검증: `prd/phase_11_task.md`
- 아키텍처 개요: `docs/architecture/overview.ko.md`
- 워크스페이스 분석: `docs/architecture/workspace-analysis.ko.md`
- 사용자 유즈케이스: `docs/architecture/user-use-cases.ko.md`
- 상세 구현 계획: `prd/phase_12_implementation_plan.md`
- 실행 추적: `prd/phase_12_task.md`

## 문서 목적

Phase 11으로 API 프로세스가 단일 live runtime session을 시작하고 중지하는 기본 orchestration은 확보되었다. 그러나 여전히 운영자 관점에서는 dashboard가 “연결된 loop를 보는 화면”에 더 가까웠고, launch 전 readiness 판단, launch 이후 incident 확인, 마지막 preflight 결과 확인, loop 부재 시 controller 상태 확인이 한 화면에서 자연스럽게 연결되지 않았다.

이번 작업은 이 간극을 메우기 위해 사실상 Phase 12에 해당하는 범위를 수행한 것으로 본다. 핵심은 새로운 거래 로직을 추가하는 것이 아니라, **운영 콘솔로서의 제품 표면을 강화**하고, structured preflight 결과를 API와 UI 계약으로 끌어올리고, runtime controller가 그 문맥을 지속적으로 보존하도록 만드는 것이다.

이 문서는 이미 수행된 작업을 phase 단위 산출물로 정리해, 왜 이 범위가 별도 phase로 볼 수 있는지, 어떤 제품 목표를 달성했는지, 무엇이 아직 후속 과제로 남는지 기록한다.

## Goal

1. live preflight를 단순 pass/fail 메시지가 아니라 운영자용 readiness contract로 확장한다.
2. API controller와 dashboard status가 마지막 preflight와 최근 incident 문맥을 유지하고 노출하게 한다.
3. dashboard를 “launch form + 상태 카드 + last preflight + incident + reconciliation”이 결합된 운영 콘솔로 강화한다.
4. guarded live launch가 UI에서도 명시적 확인 단계를 거치도록 하여 실수 가능성을 줄인다.

이번 phase는 다음 원칙을 따른다.

- 기존 live loop, risk, KIS guard의 거래 semantics는 바꾸지 않는다.
- preflight 확장은 backward compatibility를 최대한 유지한다.
- 운영자 UX 강화가 목적이므로, 새로운 브로커/시장 지원은 포함하지 않는다.
- dashboard는 정보량을 늘리되, 실제 실행 판단에 필요한 상태를 우선 배치한다.

## Current Baseline

- `POST /api/v1/live/preflight`는 `ready`, `reasons`, `quote_summary`, `quote_summaries`, `symbol_count` 중심 응답만 제공했다.
- `LiveRuntimeController`는 active session과 last error는 다뤘지만, 마지막 preflight snapshot은 보존하지 않았다.
- `GET /api/v1/dashboard/status`는 controller state와 basic runtime heartbeat는 보여줬지만, `latest_incident`, `last_preflight`, `controller_state_detail`, `broker` 같은 운영 문맥은 없었다.
- dashboard launch form은 provider/broker/mode를 선택해 start를 누르는 수준이었고, preflight를 먼저 수행해 blocking reason을 읽는 UX가 없었다.
- guarded live launch는 백엔드 KIS guard에 의존했지만, 프런트엔드에서 별도 confirmation gate는 약했다.
- README와 deploy runbook은 runtime start/stop은 설명했지만, preflight-first 운영 흐름과 readiness panel 기준은 충분히 설명하지 않았다.

## Non-Goals

- 멀티브로커 또는 미국장 지원 추가
- 주문 lifecycle durable store 도입
- run/session metadata 영속화 모델 확장
- API key lifecycle 관리 강화
- dashboard 전체 IA 재설계
- live session scheduler, cron launch, multi-instance ownership
- 브라우저 E2E 자동화 추가

## Hard Decisions

### D-1. Structured preflight를 기존 endpoint 위에서 확장한다

완전히 새로운 readiness endpoint를 만들기보다, 기존 `/api/v1/live/preflight` 응답을 확장해 `blocking_reasons`, `warnings`, `checks`, `symbol_checks`, `next_allowed_actions`, `checked_at`를 추가한다. 이렇게 하면 기존 호출자는 하위 호환 필드를 계속 사용할 수 있고, 새 운영 콘솔은 같은 endpoint를 richer contract로 소비할 수 있다.

### D-2. 마지막 preflight는 controller가 소유한다

preflight 결과를 dashboard 전용 캐시에 두지 않고 `LiveRuntimeController`가 유지하도록 했다. start route와 explicit preflight route 모두 controller에 snapshot을 기록하면, active loop가 없는 상태에서도 dashboard가 마지막 운영 판단 근거를 보여줄 수 있다.

### D-3. launch UX는 “preflight-first”를 강제하는 방향으로 간다

operator는 같은 설정으로 먼저 preflight를 수행하고, 그 결과가 fresh한 경우에만 start를 누를 수 있어야 한다. 이를 위해 launch form은 요청 payload의 signature를 기억하고, preflight 이후 설정이 바뀌면 다시 preflight를 요구한다.

### D-4. guarded live는 UI에서도 별도 확인이 필요하다

백엔드 guard만으로도 안전하지만, 실제 운영 제품에서는 UI에서 한 번 더 “이 경로는 실주문이 가능하다”는 확인을 요구하는 것이 맞다. 그래서 `live` 선택 시 provider/broker를 KIS로 고정하고, start 직전 destructive confirmation dialog를 추가했다.

## Product Requirements

### PR-1. Structured readiness contract

- `/api/v1/live/preflight`는 `ready`, `reasons`, `blocking_reasons`, `warnings`, `checks`, `symbol_checks`, `next_allowed_actions`, `checked_at`를 반환해야 한다.
- `checks`는 broker route, market session, live-order gate, symbol quote validation을 포함해야 한다.
- `symbol_checks`는 심볼별 status/pass-warn-fail과 가격/거래량 문맥을 반환해야 한다.

### PR-2. Controller-owned preflight memory

- explicit preflight 호출과 runtime start 호출 모두 마지막 preflight를 controller에 기록해야 한다.
- dashboard status는 active loop가 없어도 마지막 preflight를 반환해야 한다.

### PR-3. Dashboard operations console

- dashboard는 disconnected 상태에서도 launch console, controller status, last preflight를 보여줘야 한다.
- active 상태에서는 runtime briefing, incident, reconciliation, positions, equity, event timeline이 함께 보여야 한다.
- controller state와 runtime state 차이는 분명히 드러나야 한다.

### PR-4. Guarded live confirmation

- `live` 모드 선택 시 UI는 KIS route를 전제로 동작해야 한다.
- preflight 결과가 현재 설정과 일치하지 않으면 start는 비활성화되어야 한다.
- `live` launch는 destructive confirmation dialog를 거쳐야 한다.

### PR-5. Docs alignment

- README는 start route가 preflight snapshot을 함께 반환한다는 점을 설명해야 한다.
- 배포 runbook은 “먼저 preflight, 그 다음 start” 운영 절차를 명시해야 한다.

## Scope By Epic

### Epic A. Preflight contract 강화

목표:
- live preflight를 operator-readable readiness contract로 끌어올린다.

포함:
- `PreflightCheckResult` 확장
- API DTO 확장
- KIS preflight 결과의 blocking/warning/check/symbol-check 분류

제외:
- 새로운 exchange readiness endpoint
- historical preflight storage

### Epic B. Controller/dashboard 상태 문맥 확장

목표:
- controller와 dashboard status가 최근 운영 판단 근거를 보존하고 노출하도록 한다.

포함:
- last preflight snapshot
- latest incident 추출
- controller state detail
- broker/stop_supported/status enrichment

제외:
- event sourcing
- 별도 incident repository

### Epic C. Dashboard 운영 콘솔 UX

목표:
- launch, preflight, confirmation, monitoring이 한 흐름으로 이어지는 UI를 만든다.

포함:
- preflight-first launch form
- guarded live confirmation dialog
- runtime briefing / last preflight / latest incident / reconciliation cards

제외:
- 전면 redesign
- dashboard navigation 구조 변경

## Impacted Files

### Runtime and readiness
- `src/trading_system/app/services.py`
- `src/trading_system/app/live_runtime_controller.py`

### API routes and schemas
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/routes/live_runtime.py`
- `src/trading_system/api/routes/dashboard.py`
- `src/trading_system/api/schemas.py`

### Frontend operations console
- `frontend/components/dashboard/RuntimeLaunchForm.tsx`
- `frontend/app/dashboard/page.tsx`
- `frontend/components/dashboard/DashboardMetrics.tsx`
- `frontend/hooks/useDashboardPolling.ts`
- `frontend/lib/api/dashboard.ts`
- `frontend/lib/api/types.ts`

### Validation and docs
- `tests/unit/test_live_runtime_routes.py`
- `tests/unit/test_dashboard_routes.py`
- `tests/unit/test_api_server.py`
- `tests/unit/test_api_backtest_schema.py`
- `tests/integration/test_live_runtime_api_integration.py`
- `README.md`
- `docs/runbooks/deploy-production.md`
- `docs/runbooks/deploy-production.ko.md`

## Delivery Slices

### Slice 0. Structured preflight model 확장
- `PreflightCheckResult`와 API response DTO를 운영자용 readiness contract로 확장한다.

### Slice 1. Controller와 dashboard status enrichment
- last preflight snapshot과 latest incident를 controller/status 계약에 추가한다.

### Slice 2. Dashboard launch flow 재구성
- preflight-first launch form과 guarded live confirmation UX를 추가한다.

### Slice 3. 운영 문서와 회귀 검증 반영
- README/runbook과 관련 테스트를 새 계약에 맞춰 정리한다.

## Success Metrics

- 동일 payload에 대해 preflight 결과가 structured readiness contract로 반환된다.
- dashboard가 active loop가 없어도 controller state와 마지막 preflight를 보여준다.
- launch form은 stale preflight 상태에서 start를 막고, fresh preflight 결과가 있을 때만 진행시킨다.
- guarded live launch는 별도 UI confirmation을 거친다.
- frontend lint/build와 touched backend/service 검증이 통과한다.

## Risks and Follow-up

- 일부 `TestClient(create_app())` 기반 테스트는 현재 환경에서 lifespan startup 정체가 있어, route/service 중심 검증으로 대체되었다.
- run/session metadata 영속화와 audit trail은 여전히 후속 phase로 남는다.
- latest incident는 현재 in-memory recent event scan 기반이므로 장기 이력/검색 기능은 없다.
- dashboard는 운영 콘솔로 강화됐지만, 백테스트/run history를 같은 제품 문맥으로 묶는 작업은 아직 남아 있다.
