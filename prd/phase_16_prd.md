# Phase 16 PRD

관련 문서:
- 이전 phase 범위/결과: `prd/phase_15_prd.md`
- 이전 phase 실행 검증: `prd/phase_15_task.md`
- 아키텍처 개요: `docs/architecture/overview.ko.md`
- 워크스페이스 분석: `docs/architecture/workspace-analysis.ko.md`
- 사용자 유즈케이스: `docs/architecture/user-use-cases.ko.md`
- 상세 구현 계획: `prd/phase_16_implementation_plan.md`
- 실행 추적: `prd/phase_16_task.md`

## 문서 목적

Phase 15까지의 완료 코드는 broker open-order authority, broker order id audit propagation, order audit filter/export, strategy config parity를 구현했다. `docs/architecture`도 이 상태를 반영하며 다음 남은 갭으로 긴 backtest의 외부 worker화, 과거 live session 검색/export, KIS cancel/replace 또는 order polling, 운영 hardening을 지목한다.

코드와 문서를 함께 보면 가장 작고 직접적인 다음 구현 범위는 **과거 live runtime session을 운영 증적으로 재사용하는 것**이다. 현재 `LiveRuntimeSessionRepository.list()`는 `limit` 기반 최근 목록만 제공하고, 프론트엔드도 dashboard 안의 최근 10개 패널만 소비한다. 반면 active runtime 이벤트는 `StructuredLogger`의 in-memory ring buffer에 머물러 세션 종료 후 incident timeline을 재구성할 수 없고, historical equity도 active loop의 writer를 통해서만 읽는다.

Phase 16은 live session history를 단순 최근 목록에서 session investigation workspace로 승격한다. 목표는 session 검색/필터/export, 과거 session equity 조회, session 단위 incident/event archive, order audit과의 evidence bundle, 그리고 전용 frontend history 화면을 추가하는 것이다.

## Goal

1. live runtime session history API와 repository가 장기 검색/필터/페이지네이션/export를 지원한다.
2. 종료된 live session도 equity curve, incident event, order audit summary를 같은 session id 기준으로 조회할 수 있다.
3. active loop의 warning/error/risk/reconciliation/control event 중 운영 조사에 필요한 subset을 durable archive로 남긴다.
4. 프론트엔드는 dashboard의 최근 패널을 유지하되, 과거 session 전용 화면에서 검색, 상세 검토, CSV/JSONL export, audit export를 제공한다.
5. architecture docs와 runbook은 live session incident review workflow를 실제 API/프론트 동작과 일치하게 설명한다.

이번 phase는 다음 원칙을 따른다.

- trading decision, risk semantics, broker execution semantics는 변경하지 않는다.
- 이벤트 archive는 운영 증적용이며, 전체 structured log 수집 플랫폼을 만들지 않는다.
- order audit export의 bounded response 정책을 유지한다.
- file repository와 Supabase repository의 contract를 동시에 맞춘다.
- active dashboard monitoring과 historical session review를 같은 UI에 억지로 섞지 않는다.

## Current Baseline

- `LiveRuntimeSessionRecord`는 `session_id`, 시작/종료 시각, provider, broker, execution mode, symbols, final state, error, preflight summary를 저장한다.
- `LiveRuntimeSessionRepository.list(limit)`는 최신순 목록만 반환하며 provider/state/symbol/time 필터, total count, pagination, export가 없다.
- `/api/v1/live/runtime/sessions`는 `limit <= 100` 최근 목록만 제공한다.
- dashboard의 `SessionHistoryPanel`은 최근 10개 session을 보여주고 `SessionDetailDialog`에서 session owner 기준 order audit CSV export만 제공한다.
- `/api/v1/dashboard/events`와 SSE는 active loop의 in-memory event buffer를 읽는다. session 종료 후 runtime event timeline은 durable하게 남지 않는다.
- `/api/v1/dashboard/equity`는 active loop에 붙은 writer만 읽으므로 종료된 session id로 equity를 조회하는 route가 없다.
- order audit은 `scope=live_session`, `owner_id=session_id` 기준 조회/export가 가능하다.
- `docs/architecture/workspace-analysis.ko.md`는 "Session history UX: 최근 live runtime session은 dashboard에서 볼 수 있지만, 장기 검색과 export는 아직 없음"을 남은 갭으로 둔다.

## Non-Goals

- Redis/Celery/Kafka 등 외부 queue/worker 기반 backtest 실행 모델
- 전체 로그 수집/검색 플랫폼, OpenTelemetry collector, 외부 SIEM 연동
- 주문 cancel/replace, long-running order polling daemon, OMS 상태 머신
- live session replay를 통한 portfolio state 재계산
- 다중 사용자 RBAC, SSO, tenant 분리
- 대량 비동기 export job, object storage upload, signed URL 발급
- 전략 YAML 전체 편집 UI 또는 strategy promotion workflow

## Hard Decisions

### D-1. Historical session review는 session repository를 중심으로 확장한다

새 화면과 API의 primary key는 `session_id`다. session list/detail을 중심에 두고, equity, runtime event archive, order audit summary는 session evidence로 조합한다. order audit repository를 session 검색의 primary source로 바꾸지 않는다.

### D-2. Runtime event archive는 선별 저장으로 시작한다

모든 log event를 저장하지 않는다. Phase 16은 `WARNING` 이상, `risk.*`, `portfolio.reconciliation.*`, `system.control`, `system.error`, `system.shutdown` 같이 incident review에 직접 필요한 event만 `LiveRuntimeEventRecord`로 저장한다. active SSE/polling UX는 기존 in-memory logger를 계속 사용한다.

### D-3. Historical equity reader는 writer contract와 분리한다

현재 writer는 active session 쓰기/최근 읽기 역할을 함께 갖는다. Phase 16은 session id를 받아 file/Supabase equity를 읽는 작은 reader/factory를 추가한다. live loop에서 쓰는 writer interface를 불필요하게 넓히지 않는다.

### D-4. Export는 bounded CSV/JSONL response로 제한한다

session export와 event export는 order audit export와 같은 bounded response 정책을 따른다. 기본 limit은 보수적으로 두고, 최대 상한을 둔다. 대량 장기 보관/다운로드 파이프라인은 별도 phase로 남긴다.

### D-5. Frontend는 전용 route를 추가한다

dashboard 첫 화면은 active operations console로 유지한다. 과거 session 검색과 investigation은 `/dashboard/sessions` 같은 전용 route로 분리하고, dashboard의 최근 session panel은 해당 화면으로 이동하는 entry point로 축소한다.

## Product Requirements

### PR-1. Live session search and pagination

- session list API는 `start`, `end`, `provider`, `broker`, `live_execution`, `state`, `symbol`, `has_error`, `page`, `page_size`, `sort`를 지원해야 한다.
- response는 현재 page의 sessions와 total count를 반환해야 한다.
- file repository와 Supabase repository가 같은 필터 의미를 가져야 한다.
- invalid datetime, invalid sort, page/page_size 범위 초과는 구조화된 validation error로 반환해야 한다.

### PR-2. Session export

- session list filter와 같은 조건으로 CSV/JSONL export를 제공해야 한다.
- export 응답은 record count와 applied filters를 header 또는 metadata로 노출해야 한다.
- export는 bounded response로 제한하며 최대 record 수를 명시적으로 clamp해야 한다.

### PR-3. Historical session evidence bundle

- session detail API는 session record와 함께 order audit summary, recent order audit records, equity point count, archived incident count를 확인할 수 있어야 한다.
- 종료된 session id로 equity curve를 조회할 수 있어야 한다.
- 없는 session id는 404를 반환하고, session은 있지만 evidence가 없는 경우 빈 collection을 반환해야 한다.

### PR-4. Durable runtime event archive

- live runtime 시작 시 session id 기준 event archive writer가 연결되어야 한다.
- archive 대상 event는 severity/prefix allowlist로 제한되어야 한다.
- 저장 실패는 live loop를 멈추지 않고 warning으로만 남겨야 한다.
- file repository와 Supabase repository 모두 append/list/filter를 지원해야 한다.

### PR-5. Frontend historical session workspace

- frontend는 과거 session 전용 화면을 제공해야 한다.
- 사용자는 날짜 범위, route(provider/broker/execution), state, symbol, error 여부로 session을 좁힐 수 있어야 한다.
- session detail은 preflight summary, equity curve, incident timeline, order audit summary, order audit export action을 한 화면에서 제공해야 한다.
- active dashboard의 최근 session panel은 전용 화면으로 이동할 수 있는 entry point를 제공해야 한다.

### PR-6. Docs and runbook alignment

- architecture docs는 live session history가 검색/export/evidence bundle을 지원한다는 점과 event archive의 제한을 설명해야 한다.
- KIS live operations runbook과 incident response runbook은 session id 기준으로 session export, event archive, order audit export, broker order id 대조를 수행하는 절차를 포함해야 한다.
- release gate checklist는 historical session review 검증 항목을 포함해야 한다.

## Scope By Epic

### Epic A. Session repository query and export

목표:
- live session repository와 API를 최근 목록에서 검색 가능한 history contract로 확장한다.

포함:
- filter dataclass 또는 typed query helper
- file/Supabase list pagination과 total count
- session CSV/JSONL export route
- repository/route unit test
- Supabase migration/index 추가

제외:
- external search engine
- 비동기 export job
- session retention/prune 정책

### Epic B. Historical evidence APIs

목표:
- 종료된 session도 equity, incident, order audit 근거를 session id로 재구성한다.

포함:
- historical equity reader/factory
- session evidence DTO와 route
- order audit summary aggregation
- archived incident/event count
- route-service boundary integration test

제외:
- portfolio replay
- trade analytics를 live session 전체로 확장
- order lifecycle state machine

### Epic C. Runtime event archive

목표:
- active loop의 incident-relevant events를 session 종료 후에도 조회 가능한 durable record로 남긴다.

포함:
- `LiveRuntimeEventRecord` DTO/repository
- file/Supabase append/list/filter
- logger subscriber 또는 loop boundary wiring
- 저장 실패 isolation
- event archive tests

제외:
- 모든 structured log 영구 저장
- external observability backend
- full-text event search

### Epic D. Frontend historical session review

목표:
- 운영자가 브라우저에서 과거 live session을 검색하고 증적을 내려받을 수 있게 한다.

포함:
- `/dashboard/sessions` route
- filter form, paginated table, detail panel/dialog
- historical equity chart reuse
- incident timeline
- session export와 order audit export action
- Playwright smoke update

제외:
- active live loop control을 historical 화면으로 이동
- UI 기반 config editor
- 대량 다운로드 진행률 UI

### Epic E. Documentation and release gates

목표:
- 구현된 historical review workflow를 운영 문서와 검증 기준에 반영한다.

포함:
- architecture docs 업데이트
- KIS live operations runbook 업데이트
- incident response runbook 업데이트
- deploy/migration notes 업데이트
- release gate checklist 업데이트

제외:
- 별도 ADR 작성
- 외부 운영 매뉴얼 배포 자동화

## Impacted Files

### Live session repository and API
- `src/trading_system/app/live_runtime_history.py`
- `src/trading_system/api/routes/live_runtime.py`
- `src/trading_system/api/schemas.py`
- `scripts/migrations/005_add_live_runtime_event_archive.sql`
- `tests/unit/test_live_runtime_history.py`
- `tests/unit/test_live_runtime_routes.py`
- `tests/integration/test_live_runtime_api_integration.py`

### Historical equity and evidence
- `src/trading_system/app/equity_writer.py`
- `src/trading_system/app/supabase_equity_writer.py`
- `src/trading_system/execution/order_audit.py`
- `src/trading_system/api/routes/live_runtime.py`
- `tests/unit/test_equity_timeseries.py`
- `tests/unit/test_supabase_equity_writer.py`
- `tests/unit/test_order_audit_repository.py`
- `tests/integration/test_live_runtime_api_integration.py`

### Runtime event archive
- `src/trading_system/app/live_runtime_events.py`
- `src/trading_system/app/live_runtime_controller.py`
- `src/trading_system/app/loop.py`
- `src/trading_system/app/services.py`
- `src/trading_system/core/ops.py`
- `tests/unit/test_live_runtime_events.py`
- `tests/unit/test_live_runtime_controller.py`
- `tests/unit/test_live_loop.py`

### Frontend historical session review
- `frontend/lib/api/types.ts`
- `frontend/lib/api/dashboard.ts`
- `frontend/components/layout/NavBar.tsx`
- `frontend/components/dashboard/SessionHistoryPanel.tsx`
- `frontend/components/dashboard/SessionDetailDialog.tsx`
- `frontend/app/dashboard/sessions/page.tsx`
- `frontend/e2e/smoke.spec.ts`

### Documentation and operator notes
- `README.md`
- `docs/architecture/overview.ko.md`
- `docs/architecture/overview.md`
- `docs/architecture/workspace-analysis.ko.md`
- `docs/architecture/workspace-analysis.md`
- `docs/architecture/user-use-cases.ko.md`
- `docs/architecture/user-use-cases.md`
- `docs/runbooks/kis-domestic-live-operations.ko.md`
- `docs/runbooks/kis-domestic-live-operations.md`
- `docs/runbooks/incident-response.ko.md`
- `docs/runbooks/incident-response.md`
- `docs/runbooks/deploy-production.ko.md`
- `docs/runbooks/deploy-production.md`
- `docs/runbooks/release-gate-checklist.ko.md`
- `docs/runbooks/release-gate-checklist.md`

## Delivery Slices

### Slice 0. Session search contract
- repository filter/pagination contract와 list API를 확장한다.

### Slice 1. Session export
- session CSV/JSONL export route와 file/Supabase filtering parity를 추가한다.

### Slice 2. Historical evidence APIs
- 종료된 session의 equity, order audit summary, event archive summary를 조회하는 API를 추가한다.

### Slice 3. Runtime event archive
- incident-relevant runtime events를 durable archive로 저장하고 조회한다.

### Slice 4. Frontend session history workspace
- 전용 session history 화면, 필터, detail/evidence UI, export action을 구현한다.

### Slice 5. Docs and release gate alignment
- architecture docs, runbooks, deploy notes, release checklist를 새 workflow에 맞춘다.

## Success Metrics

- live session list API가 state/provider/symbol/time 필터와 pagination total을 file/Supabase repository에서 같은 의미로 반환한다.
- session export API가 applied filter와 record count를 포함한 CSV/JSONL bounded response를 반환한다.
- 종료된 session id로 equity points, incident events, order audit summary를 조회할 수 있다.
- event archive 저장 실패가 live loop tick, stop, session finalization을 실패시키지 않는다.
- frontend `/dashboard/sessions`에서 필터링, detail 조회, session export, order audit export를 수행할 수 있다.
- architecture docs와 runbooks가 최근 panel 중심 설명에서 historical session review workflow로 갱신된다.

## Risks and Follow-up

- Runtime event archive는 선별 저장이므로 모든 debug-level event를 재구성할 수 없다.
- File repository index가 커질 경우 장기적으로 retention/prune 또는 compact 작업이 필요하다.
- Supabase migration 적용 전 배포 환경에서는 event archive table이 없을 수 있으므로 deploy runbook과 startup error를 명확히 해야 한다.
- Session evidence bundle은 live trade analytics 전체를 대체하지 않는다. live session trade analytics는 별도 phase 후보로 남긴다.
- 외부 worker 기반 backtest 실행과 KIS cancel/replace workflow는 여전히 별도 backlog다.
