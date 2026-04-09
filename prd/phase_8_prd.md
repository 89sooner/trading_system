# Phase 8 PRD

관련 문서:
- 이전 phase 범위/결과: `prd/phase_7_5_prd.md`
- 이전 phase 실행 검증: `prd/phase_7_5_task.md`
- 상세 구현 계획: `prd/phase_8_implementation_plan.md`
- 실행 추적: `prd/phase_8_task.md`
- Codex 리뷰: `prd/phase_8_plan_review_from_codex.md`

## 문서 목적

이 문서는 Phase 7.5까지 구축된 트레이딩 시스템의 운영 기반 위에 **데이터 영속화, 서버 측 런 관리, 실시간 이벤트 스트리밍, 운영 알림 채널**을 도입하는 `Phase 8` 범위를 정의한다.

현재 시스템은 백테스트 결과가 `InMemoryBacktestRunRepository`에만 저장되어 서버 재시작 시 유실되고, 프론트엔드의 `/runs` 목록이 localStorage 기반 `runsStore`에 의존하며, 대시보드의 equity 시계열이 클라이언트 측 polling 누적에 의존하여 새로고침 시 초기화되고, 라이브 이벤트가 HTTP polling(5초 간격)에만 의존하는 구조적 한계가 있다.

Phase 8은 이러한 운영 신뢰성 공백을 해소하여, 서버 재시작 후에도 실행 이력이 보존되고, 운영자가 실시간으로 이벤트를 수신하며, 외부 채널로 핵심 이벤트를 통보받을 수 있는 시스템으로 전환하는 것을 목표로 한다.

## Goal

1. 백테스트 런 결과를 파일 기반으로 영속화하여 서버 재시작 후에도 이력을 보존한다.
2. 서버 측 런 목록/검색 API를 제공하여 프론트엔드의 localStorage 의존을 제거한다.
3. 라이브 루프의 포트폴리오 시계열을 서버 측에서 저장하여 대시보드 새로고침 후에도 equity chart를 복원한다.
4. SSE(Server-Sent Events) 기반 실시간 이벤트 스트리밍을 도입하여 대시보드 polling 의존을 제거한다.
5. Webhook 기반 운영 알림 채널을 도입하여 거래 체결, 리스크 거절, 시스템 이상 이벤트를 외부로 전달한다.

구현은 반드시 다음 원칙을 지켜야 한다.

- 외부 데이터베이스(PostgreSQL, Redis 등)를 도입하지 않고 파일 기반 영속화(JSON 파일)를 사용한다.
- 기존 API contract(`/api/v1/*`)의 하위 호환성을 유지한다. 기존 엔드포인트의 응답 형태를 변경하지 않는다.
- SSE는 기존 polling 엔드포인트를 대체하지 않고 보완한다. 프론트엔드는 SSE 우선 + polling fallback 전략을 사용한다.
- Webhook 설정은 env-var 기반으로 `build_services()` 경로에 통합하며, webhook이 미설정된 경우 기존 동작에 영향을 주지 않는다.
- 프론트엔드 변경은 SSE 연동, 런 목록 API 전환, equity chart 서버 데이터 전환에 한정한다.

## Current Baseline

- `BacktestRunRepository` Protocol: `save(run)`, `get(run_id)`, `clear()` — 3개 메서드
- `InMemoryBacktestRunRepository`: `dict[str, BacktestRunDTO]` 기반 in-memory 구현이 유일한 구현체
- `_RUN_REPOSITORY = InMemoryBacktestRunRepository()` — `api/routes/backtest.py` 모듈 수준 singleton
- `BacktestRunDTO`: `run_id`, `status`, `started_at`, `finished_at`, `input_symbols`, `mode`, `result`, `error` 필드
- 프론트엔드 `/runs` 페이지: `runsStore`(localStorage)에서 run ID 목록을 읽어 `GET /api/v1/backtests/{run_id}`로 개별 fetch
- 프론트엔드 대시보드: `useDashboardPolling` 훅에서 5초 간격 HTTP polling → `computePortfolioValue()` → 클라이언트 측 시계열 누적 (최대 300포인트, 새로고침 시 초기화)
- `StructuredLogger`: `deque(maxlen=500)` 기반 이벤트 링 버퍼, `recent_events(limit)` 메서드
- `PatternAlertService`: `evaluate()` → `PatternAlert` 반환, 외부 전달 채널 없음
- YAML loader: `configs/base.yaml` 기반 설정 지원 (`app.reconciliation_interval`, `portfolio_risk` 포함)
- Phase 7.5 완료: Playwright e2e 하네스, equity chart, 런 상세 탭 레이아웃
- Phase 6 완료: multi-symbol preflight, pending order hardening, config parity

## Non-Goals

- 외부 데이터베이스(PostgreSQL, SQLite, Redis) 도입
- WebSocket 양방향 통신 (SSE 단방향 스트리밍으로 충분)
- 프론트엔드 전면 UI 재설계 (SSE 연동 + API 전환에 한정)
- 인증/인가 시스템 변경 (기존 API key 기반 유지)
- 백테스트 결과 비교 뷰 (Phase 9 이후)
- CI/CD 파이프라인 구축
- 이메일/SMS 알림 채널 (webhook으로 한정)
- 백테스트 실행 큐잉/비동기 실행 (현재 동기 실행 유지)
- 라이브 루프 이벤트의 장기 아카이빙/검색
- Slack/Discord 네이티브 연동 (webhook URL 기반으로 대부분 커버 가능)

## Hard Decisions

### D-1. JSON 파일 기반 영속화를 선택한다 (SQLite 대신)

- SQLite는 단일 파일 DB로 적합하지만, 현재 시스템의 규모(동시 쓰기 낮음, 단일 프로세스)에서는 JSON 파일이 더 단순하다.
- `data/runs/` 디렉토리에 `{run_id}.json` 파일로 개별 저장한다.
- 런 목록은 디렉토리 스캔 + 메타데이터 인덱스 파일(`data/runs/_index.json`)로 구현한다.
- 인덱스 파일은 `run_id`, `status`, `started_at`, `input_symbols`, `mode` 등 목록 표시에 필요한 경량 메타데이터만 포함한다.
- 향후 동시성/성능 요구가 커지면 SQLite로 교체할 수 있는 인터페이스 경계를 유지한다.
- **Source-of-truth**: 개별 run file(`{run_id}.json`)이 진실 원천이다. `_index.json`은 rebuildable cache로 취급한다.
- **Atomic write**: 파일 저장은 temp file → `os.replace()` atomic rename 패턴을 사용하여 partial write를 방지한다.
- **복구 전략**: 서버 시작 시 `_index.json`이 없거나 깨진 경우, `data/runs/` 디렉토리의 개별 파일을 스캔하여 인덱스를 재구축한다. run file 저장 → index 갱신 순서로 수행하므로, index 갱신 실패 시에도 run file은 보존되어 다음 시작 시 복구 가능하다.

### D-2. SSE는 기존 polling을 대체하지 않고 보완한다

- `GET /api/v1/dashboard/stream` SSE 엔드포인트를 신규 추가한다.
- SSE 경로가 `/api/v1/dashboard/stream`이므로 기존 `dashboard.py` 라우터에 추가한다. 별도 `stream.py` 파일을 만들지 않으며, `server.py`에 추가 라우터 등록도 불필요하다.
- 기존 `GET /api/v1/dashboard/status`, `/positions`, `/events` 엔드포인트는 그대로 유지한다.
- 프론트엔드는 `EventSource` 연결 성공 시 polling 간격을 줄이거나 비활성화하고, 연결 실패 시 기존 polling으로 fallback한다.
- SSE 이벤트 타입: `status`, `position`, `event`, `equity`, `heartbeat`
- SSE 연결은 API key를 query parameter로 전달한다 (`EventSource`가 커스텀 헤더를 지원하지 않음).

### D-3. Webhook은 fire-and-forget 방식으로 비동기 전송한다

- `StructuredLogger.emit()` 호출 시 webhook 대상 이벤트를 비동기로 외부 URL에 POST한다.
- webhook 전송 실패는 로그에 기록하되, 트레이딩 로직에 영향을 주지 않는다 (fire-and-forget).
- webhook 대상 이벤트는 설정으로 필터링한다: `order.filled`, `risk.rejected`, `pattern.alert`, `system.error` 등.
- webhook 설정은 env-var 전용으로 `build_services()` 경로에 통합한다: `TRADING_SYSTEM_WEBHOOK_URL`, `TRADING_SYSTEM_WEBHOOK_EVENTS`, `TRADING_SYSTEM_WEBHOOK_TIMEOUT`. 현재 runtime 서비스 조립은 `app/settings.py`의 `AppSettings` → `build_services()`를 사용하며, `config/settings.py`의 YAML loader는 이 경로에 관여하지 않으므로 YAML loader 확장은 하지 않는다. `configs/base.yaml`에는 예시 주석만 추가한다.
- `httpx.AsyncClient`를 사용하되, 라이브 루프가 동기 컨텍스트이므로 별도 daemon thread에서 비동기 전송한다.

### D-4. 포트폴리오 시계열은 라이브 루프에서 주기적으로 파일에 기록한다

- 라이브 루프의 heartbeat 주기마다 현재 portfolio value를 계산하여 `data/equity/{session_id}.jsonl` (JSON Lines)에 append한다.
- `GET /api/v1/dashboard/equity` 엔드포인트를 추가하여 현재 세션의 equity 시계열을 반환한다.
- 프론트엔드 `EquityChart`는 페이지 로드 시 서버 API에서 히스토리를 가져오고, 이후 SSE `equity` 이벤트로 실시간 업데이트한다.
- **JSONL은 append-only로 기록한다.** write 시점에서 truncation을 수행하지 않는다. `GET /api/v1/dashboard/equity` 읽기 시 파일 끝에서 최근 N개 라인만 반환한다. physical compaction은 Phase 8 범위 밖으로 두고, 장기 실행 시 파일 크기 관리는 Phase 9 이후 검토한다.

### D-5. 런 목록 API는 인덱스 파일 기반 경량 조회를 사용한다

- `GET /api/v1/backtests` 목록 엔드포인트를 신규 추가한다.
- 인덱스 파일(`_index.json`)에서 메타데이터를 읽어 페이지네이션, 상태 필터링을 지원한다.
- 개별 런의 전체 결과(`result` 필드)는 목록 응답에 포함하지 않는다 (경량화).
- 인덱스 파일은 런 저장/삭제 시 동기적으로 갱신한다.
- 프론트엔드 `/runs` 페이지는 서버 목록 API로 전환하되, `runsStore`는 fallback으로 유지한다.

## Product Requirements

### PR-1. 파일 기반 백테스트 런 영속화

- `FileBacktestRunRepository`를 `BacktestRunRepository` Protocol 구현으로 추가한다.
- 런 데이터는 `data/runs/{run_id}.json`에 개별 저장한다.
- 메타데이터 인덱스는 `data/runs/_index.json`에 유지한다.
- `InMemoryBacktestRunRepository`는 테스트 용도로 유지하되, 기본 구현은 `FileBacktestRunRepository`로 교체한다.
- 서버 시작 시 기존 `data/runs/` 디렉토리에서 인덱스를 복구할 수 있어야 한다.
- `data/runs/` 디렉토리가 없으면 자동 생성한다.

### PR-2. 서버 측 런 목록/검색 API

- `GET /api/v1/backtests` 엔드포인트를 추가한다.
- 응답: `{ "runs": [...], "total": N, "page": P, "page_size": S }`
- 각 런 항목은 `run_id`, `status`, `started_at`, `finished_at`, `input_symbols`, `mode`를 포함한다 (result 미포함).
- 쿼리 파라미터: `page` (기본 1), `page_size` (기본 20, 최대 100), `status` (필터), `mode` (필터).
- 정렬: `started_at` 역순 (최신 먼저).
- 기존 `GET /api/v1/backtests/{run_id}` 엔드포인트는 변경 없이 유지한다.

### PR-3. 서버 측 포트폴리오 시계열 저장 및 조회

- 라이브 루프에서 heartbeat 주기(기본 60초)마다 portfolio equity snapshot을 `data/equity/{session_id}.jsonl`에 append한다.
- snapshot 형식: `{"timestamp": "...", "equity": "...", "cash": "...", "positions_value": "..."}`
- `GET /api/v1/dashboard/equity` 엔드포인트를 추가한다.
- 응답: `{ "session_id": "...", "points": [...], "total": N }`
- 쿼리 파라미터: `limit` (기본 300, 최대 1000) — 최근 N개 포인트 반환.
- 프론트엔드 `EquityChart`는 페이지 로드 시 이 API에서 히스토리를 가져온다.

### PR-4. SSE 기반 실시간 이벤트 스트리밍

- `GET /api/v1/dashboard/stream` SSE 엔드포인트를 `dashboard.py` 라우터에 추가한다.
- 인증: SSE endpoint 함수 내에서 `request.query_params.get("api_key")`를 직접 읽어 검증한다. `security.py` 미들웨어의 `_extract_api_key()`를 전역 수정하지 않는다. 이를 통해 기존 보안 표면을 넓히지 않고 SSE만 query param을 허용한다.
- SSE 이벤트 타입별 발행 원천:

  | 이벤트 타입 | 발행 원천 | 트리거 |
  |---|---|---|
  | `event` | `StructuredLogger` subscriber callback | `logger.emit()` 호출 시 |
  | `heartbeat` | SSE endpoint 자체 | 15초 간격 timer |
  | `equity` | 라이브 루프 equity snapshot 기록 시점 | `_check_heartbeat()` 내 equity append 시 `logger.emit("sse.equity", ...)` |
  | `status` | 라이브 루프 state transition | `loop.state` setter 변경 시 `logger.emit("sse.status", ...)` |
  | `position` | `execute_trading_step()` 후 portfolio 변경 감지 | tick 실행 후 position snapshot 비교 시 `logger.emit("sse.position", ...)` |

- 구현 방식: `StructuredLogger`에 subscriber callback 리스트를 추가한다. `emit()` 호출 시 등록된 모든 subscriber에게 `EventRecord`를 전달한다. SSE endpoint는 `asyncio.Queue`를 subscriber로 등록하여 이벤트를 수신한다.
- 각 이벤트의 `data` 필드는 기존 REST 응답 DTO와 동일한 JSON 형태를 사용한다.
- 연결 수 제한: 서버당 최대 10개 동시 SSE 연결.
- 프론트엔드: `EventSource` 연결 성공 시 polling 비활성화, 실패 시 polling fallback.

### PR-5. Webhook 기반 운영 알림 채널

- `WebhookNotifier` 서비스를 추가한다.
- 설정: env-var `TRADING_SYSTEM_WEBHOOK_URL`, `TRADING_SYSTEM_WEBHOOK_EVENTS`, `TRADING_SYSTEM_WEBHOOK_TIMEOUT`. `build_services()` 내에서 env-var를 읽어 생성한다.
- 대상 이벤트 기본값: `order.filled`, `risk.rejected`, `pattern.alert`, `system.error`, `portfolio.reconciliation.position_adjusted`.
- webhook payload: `{ "event": "...", "timestamp": "...", "payload": {...}, "source": "trading-system" }`
- 전송 실패 시 1회 재시도 후 로그 기록, 트레이딩 로직 비차단.
- webhook URL이 미설정이면 `WebhookNotifier`가 no-op으로 동작한다.

### PR-6. 프론트엔드 통합

- `/runs` 페이지: `GET /api/v1/backtests` 목록 API로 전환. 서버 API 실패 시 `runsStore` fallback 유지.
- 대시보드: `EventSource` 기반 SSE 연동. `useDashboardPolling` 훅을 `useDashboardStream` 훅으로 확장.
- `EquityChart`: 페이지 로드 시 `GET /api/v1/dashboard/equity`에서 히스토리 조회 + SSE `equity` 이벤트로 실시간 추가.
- SSE 연결 실패/미지원 시 기존 polling으로 자동 fallback.
- 기존 UI 레이아웃/디자인 변경 없음.

## Scope By Epic

### Epic A. 파일 기반 런 영속화 + 목록 API

목표:
- 백테스트 런 결과를 서버 재시작 후에도 보존하고, 서버 측 목록/검색 API를 제공한다.

포함:
- `FileBacktestRunRepository` 구현
- 인덱스 파일 관리 (`_index.json`)
- `GET /api/v1/backtests` 목록 엔드포인트
- 기본 repository를 `FileBacktestRunRepository`로 교체
- 서버 시작 시 인덱스 복구
- 단위/통합 테스트

제외:
- SQLite/PostgreSQL 기반 저장소
- 런 삭제/아카이빙 API
- 백테스트 결과 비교 기능

### Epic B. 서버 측 포트폴리오 시계열

목표:
- 라이브 루프의 equity 히스토리를 서버 측에서 저장하여 페이지 새로고침 후에도 복원 가능하게 한다.

포함:
- 라이브 루프에서 equity snapshot 주기적 기록 (JSONL)
- `GET /api/v1/dashboard/equity` 엔드포인트
- 세션별 JSONL 파일 관리

제외:
- 히스토리컬 세션 간 비교
- equity 데이터의 장기 아카이빙
- 백테스트 결과의 서버 측 시계열 (이미 `BacktestResultDTO.equity_curve`에 포함)

### Epic C. SSE 실시간 이벤트 스트리밍

목표:
- HTTP polling 대신 SSE로 대시보드 이벤트를 실시간 푸시한다.

포함:
- `GET /api/v1/dashboard/stream` SSE 엔드포인트
- 이벤트 타입: status, position, event, equity, heartbeat
- SSE 연결 관리 (최대 동시 연결 수 제한)
- API key query parameter 인증
- 프론트엔드 `EventSource` 연동 + polling fallback

제외:
- WebSocket 양방향 통신
- SSE 이벤트 히스토리/재전송 (Last-Event-ID)
- 기존 polling 엔드포인트 제거

### Epic D. Webhook 알림 채널

목표:
- 운영 핵심 이벤트를 외부 webhook URL로 전달하여 운영자가 별도 채널에서 알림을 받을 수 있게 한다.

포함:
- `WebhookNotifier` 서비스
- env-var 기반 설정 (`build_services()` 경로)
- 이벤트 필터링
- 비동기 fire-and-forget 전송 + 1회 재시도
- 단위 테스트

제외:
- Slack/Discord 네이티브 API 연동
- 이메일/SMS 채널
- webhook 전송 이력 저장
- webhook 설정 런타임 변경 API

### Epic E. 프론트엔드 통합

목표:
- 프론트엔드를 새 API(런 목록, equity 히스토리, SSE)에 연동한다.

포함:
- `/runs` 페이지 서버 목록 API 전환
- `useDashboardStream` 훅 (SSE + polling fallback)
- `EquityChart` 서버 히스토리 연동
- 프론트엔드 API 타입/클라이언트 추가
- e2e smoke test 갱신 (필요 시)

제외:
- UI 레이아웃/디자인 변경
- 새로운 페이지 추가
- 런 비교 뷰

## Impacted Files

### 신규 생성 (백엔드)
- `src/trading_system/backtest/file_repository.py`
- `src/trading_system/notifications/__init__.py`
- `src/trading_system/notifications/webhook.py`
- `src/trading_system/app/equity_writer.py`
- `tests/unit/test_file_repository.py`
- `tests/unit/test_webhook_notifier.py`
- `tests/unit/test_sse_stream.py`
- `tests/unit/test_equity_timeseries.py`
- `tests/integration/test_run_persistence_integration.py`

### 수정 대상 (백엔드)
- `src/trading_system/backtest/repository.py` — Protocol에 `list()`, `delete()` 메서드 추가
- `src/trading_system/api/routes/backtest.py` — FileRepository 교체, 목록 엔드포인트 추가
- `src/trading_system/api/routes/dashboard.py` — equity 엔드포인트 추가, SSE 스트림 엔드포인트 추가 (별도 `stream.py` 불필요)
- `src/trading_system/api/schemas.py` — 목록/equity DTO 추가
- `src/trading_system/app/loop.py` — equity snapshot 기록, SSE 이벤트 발행 (`sse.status`, `sse.position`, `sse.equity`)
- `src/trading_system/app/services.py` — WebhookNotifier 생성 및 logger subscriber 등록
- `src/trading_system/core/ops.py` — StructuredLogger에 subscriber/callback 메커니즘 추가
- `configs/base.yaml` — webhook 설정 예시 주석 추가 (실제 파싱하지 않음)

### 수정 대상 (프론트엔드)
- `frontend/lib/api/backtests.ts` — 목록 API 클라이언트 추가
- `frontend/lib/api/dashboard.ts` — equity API 클라이언트 추가
- `frontend/lib/api/types.ts` — 새 DTO 타입 추가
- `frontend/hooks/useDashboardPolling.ts` → `useDashboardStream.ts` — SSE 연동
- `frontend/app/runs/page.tsx` — 서버 목록 API 전환
- `frontend/components/dashboard/EquityChart.tsx` — 서버 히스토리 연동

### 문서
- `README.md` — SSE, webhook, 런 영속화 문서 추가
- `docs/runbooks/` — webhook 설정 가이드
- `configs/base.yaml` — webhook env-var 설정 예시 주석 추가
- `examples/` — webhook env-var 설정 예시 추가

## Delivery Slices

### Slice 0. 파일 기반 런 영속화

- `FileBacktestRunRepository` 구현 (save/get/list/clear)
- 인덱스 파일 관리 로직
- 기존 모듈 singleton을 FileRepository로 교체
- 단위/통합 테스트

### Slice 1. 런 목록 API + 프론트엔드 전환

- `GET /api/v1/backtests` 목록 엔드포인트 (페이지네이션, 필터)
- 프론트엔드 `/runs` 페이지 서버 API 전환
- `BacktestRunRepository` Protocol에 `list()` 추가

### Slice 2. 서버 측 포트폴리오 시계열

- 라이브 루프에서 equity snapshot JSONL 기록
- `GET /api/v1/dashboard/equity` 엔드포인트
- 프론트엔드 `EquityChart` 서버 히스토리 연동

### Slice 3. SSE 실시간 스트리밍

- `GET /api/v1/dashboard/stream` SSE 엔드포인트
- StructuredLogger subscriber 메커니즘
- SSE 연결 관리 (heartbeat, 최대 연결 수)
- API key query parameter 인증 지원
- 프론트엔드 `useDashboardStream` 훅 (SSE + polling fallback)

### Slice 4. Webhook 알림 채널

- `WebhookNotifier` 서비스 구현
- env-var 기반 `build_services()` 경로 통합
- StructuredLogger → WebhookNotifier 연결
- 단위 테스트

### Slice 5. 통합 검증 및 문서

- 전체 회귀 테스트 실행
- `tsc --noEmit`, `lint`, `next build`, `test:e2e` 통과 확인
- `pytest` 전체 실행 통과 확인
- README, runbook, config 예시 갱신

## Success Metrics

- 서버 재시작 후 `GET /api/v1/backtests` 목록에서 이전 런이 조회된다
- `GET /api/v1/backtests/{run_id}`로 영속화된 런 결과를 온전히 복원할 수 있다
- `GET /api/v1/backtests` 목록 API가 page/page_size/status/mode 파라미터를 지원한다
- 대시보드 페이지 새로고침 후 `GET /api/v1/dashboard/equity`에서 히스토리컬 equity 시계열이 복원된다
- SSE `/api/v1/dashboard/stream` 연결 시 status/position/event/equity 이벤트가 실시간 수신된다
- SSE 연결 실패 시 프론트엔드가 polling으로 자동 fallback한다
- webhook URL 설정 시 `order.filled`, `risk.rejected` 이벤트가 외부 URL로 POST된다
- webhook 미설정 시 기존 동작에 영향 없다
- `pytest` 전체 테스트 통과
- `tsc --noEmit` PASS, `npm run lint` PASS, `next build` PASS
- `npm run test:e2e` smoke test 통과

## Risks and Follow-up

- JSON 파일 기반 영속화는 대량 런(수천 건 이상) 축적 시 인덱스 파일 크기와 디렉토리 스캔 성능이 저하될 수 있다. 초기에는 문제없으나, 장기적으로 SQLite 또는 분할 인덱스 전략이 필요할 수 있다.
- SSE `EventSource`는 커스텀 헤더를 지원하지 않아 API key를 query parameter로 전달해야 한다. 이는 URL에 키가 노출되므로 HTTPS 환경을 전제한다. query param 인증은 SSE endpoint 전용이며 `security.py` 전역 수정은 하지 않는다. 향후 short-lived token 발행 API로 전환할 수 있다.
- SSE 연결 수 제한(10개)은 다중 브라우저 탭에서 문제가 될 수 있다. 탭 간 `BroadcastChannel` 공유 또는 SharedWorker 패턴은 Phase 9 이후 검토한다.
- webhook 전송이 비동기 fire-and-forget이므로 전송 실패를 운영자가 인지하지 못할 수 있다. 실패 시 `system.webhook.failed` 이벤트를 logger에 emit하여 대시보드에서 확인 가능하게 한다. webhook 상태 확인 API는 Phase 9 이후 검토한다.
- equity JSONL은 append-only로 기록하므로 장기 실행 시 파일 크기가 증가한다. 읽기 시 최근 N개만 반환하여 API 응답 크기는 제한되지만, physical compaction은 Phase 9 이후 검토한다.
- `httpx` 라이브러리가 현재 의존성에 포함되어 있지 않을 수 있다. webhook 구현 시 `httpx`를 추가해야 한다.
- 기존 `_RUN_REPOSITORY` 모듈 singleton을 `FileBacktestRunRepository`로 교체할 때, 테스트에서 InMemory를 계속 사용해야 하므로 의존성 주입 경계를 명확히 해야 한다. `InMemoryBacktestRunRepository`에도 `list()`, `delete()`를 함께 구현한다.
- webhook 설정은 env-var 전용(`build_services()` 경로)이며 YAML loader에는 통합하지 않는다. `configs/base.yaml`에는 예시 주석만 추가한다.
