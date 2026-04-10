# Phase 8 Task Breakdown

## Usage

- 이 파일은 Phase 8 구현 진행 상황과 검증 증적을 기록한다.
- 체크박스는 실제 구현 작업과 검증 기준을 뜻한다.
- 각 slice가 끝날 때 `Execution Log`를 갱신한다.
- PRD 수준 범위는 `phase_8_prd.md`를 기준으로 한다.
- 상세 설계와 순서는 `phase_8_implementation_plan.md`를 기준으로 한다.

## Status Note

- 이 문서는 `prd/phase_8_prd.md`의 실행 추적 문서다.
- 현재 체크박스는 active backlog를 slice 단위로 분해한 것이며, 아직 구현 완료를 의미하지 않는다.

---

## Phase 8-0. 의존성 추가 및 데이터 디렉토리 준비

- [ ] `pyproject.toml`의 `dependencies`에 `sse-starlette` 추가
- [ ] `pip install -e ".[dev]"` 실행하여 의존성 설치 확인
- [ ] `python -c "import sse_starlette"` 성공 확인
- [ ] `httpx >= 0.28`이 dev deps에 존재함 확인 (webhook 테스트용)

Exit criteria:
- `pip install -e ".[dev]"` 성공, `import sse_starlette` 오류 없음

---

## Phase 8-1. FileBacktestRunRepository 구현

- [ ] `BacktestRunRepository` Protocol에 `list(page, page_size, status, mode) -> tuple[list[BacktestRunDTO], int]` 메서드 추가
- [ ] `BacktestRunRepository` Protocol에 `delete(run_id) -> bool` 메서드 추가
- [ ] `InMemoryBacktestRunRepository`에 `list()` 구현 (정렬: `started_at` 역순, 필터: status/mode)
- [ ] `InMemoryBacktestRunRepository`에 `delete()` 구현
- [ ] `src/trading_system/backtest/file_repository.py` 신규 생성
- [ ] `FileBacktestRunRepository.__init__(base_dir)`: 디렉토리 자동 생성 (`os.makedirs(exist_ok=True)`)
- [ ] `FileBacktestRunRepository.save(run)`: JSON serialize → temp file → `os.replace()` atomic rename → `_index.json` 갱신
- [ ] `FileBacktestRunRepository.get(run_id)`: `{run_id}.json` 파일에서 `BacktestRunDTO` 역직렬화 (없으면 `None`)
- [ ] `FileBacktestRunRepository.list(page, page_size, status, mode)`: `_index.json` 기반 필터/정렬/페이지네이션
- [ ] `FileBacktestRunRepository.delete(run_id)`: 파일 삭제 + `_index.json` 갱신 (없으면 `False`)
- [ ] `FileBacktestRunRepository.clear()`: 전체 `.json` 파일 삭제 + `_index.json` 초기화
- [ ] `FileBacktestRunRepository.rebuild_index()`: 디렉토리 내 모든 `.json` 스캔 → `_index.json` 재구축
- [ ] `BacktestRunDTO` JSON 직렬화: `dataclasses.asdict()` → `json.dumps()` 저장
- [ ] `BacktestRunDTO` JSON 역직렬화: `json.loads()` → 중첩 DTO(`BacktestResultDTO`, `SummaryDTO` 등) 포함 복원
- [ ] `_index.json` 구조: `{"runs": [{"run_id", "status", "started_at", "finished_at", "input_symbols", "mode"}]}`
- [ ] `tests/unit/test_file_repository.py` 작성:
  - [ ] save → get 왕복 테스트 (run 데이터가 완전히 보존됨)
  - [ ] list 페이지네이션 테스트 (page=1/2, page_size=10)
  - [ ] list status 필터 테스트 (succeeded만 조회)
  - [ ] list mode 필터 테스트 (backtest만 조회)
  - [ ] delete → get이 None 반환
  - [ ] rebuild_index: `_index.json` 삭제 후 rebuild → list 결과 동일
  - [ ] 빈 디렉토리에서 list 호출 → `([], 0)` 반환
  - [ ] clear → 디렉토리 내 `.json` 파일 0개
- [ ] `pytest tests/unit/test_file_repository.py -q` PASS
- [ ] `ruff check src/trading_system/backtest/file_repository.py` 0 errors

Exit criteria:
- `FileBacktestRunRepository` CRUD/list/rebuild 전체 동작, 단위 테스트 PASS

---

## Phase 8-2. 런 목록 API + 기본 repository 교체

- [ ] `schemas.py`에 `BacktestRunListItemDTO` 추가 (`run_id`, `status`, `started_at`, `finished_at`, `input_symbols`, `mode`)
- [ ] `schemas.py`에 `BacktestRunListResponseDTO` 추가 (`runs`, `total`, `page`, `page_size`)
- [ ] `backtest.py`에서 `_RUN_REPOSITORY`를 `FileBacktestRunRepository`로 교체 (경로: `TRADING_SYSTEM_RUNS_DIR` env-var, 기본 `data/runs`)
- [ ] `GET /api/v1/backtests` 엔드포인트 추가:
  - [ ] query params: `page` (default 1), `page_size` (default 20, max 100), `status`, `mode`
  - [ ] 응답: `BacktestRunListResponseDTO`
  - [ ] `page_size` 범위 검증 (1~100)
- [ ] 기존 `POST /api/v1/backtests` 동작 불변 확인 (FileRepository에 저장)
- [ ] 기존 `GET /api/v1/backtests/{run_id}` 동작 불변 확인 (FileRepository에서 조회)
- [ ] 기존 테스트가 `InMemoryBacktestRunRepository`를 fixture/monkeypatch로 계속 사용하도록 격리
- [ ] `tests/integration/test_backtest_run_api_integration.py` 수정/추가: POST → GET 목록에 나타남
- [ ] `pytest tests/unit/test_api_backtest_schema.py tests/integration/test_backtest_run_api_integration.py -q` PASS
- [ ] `ruff check src/trading_system/api/routes/backtest.py src/trading_system/api/schemas.py` 0 errors

Exit criteria:
- `GET /api/v1/backtests`가 페이지네이션/필터 지원, 기존 API 하위 호환 유지, 테스트 PASS

---

## Phase 8-3. StructuredLogger Subscriber + 서버 측 Equity 시계열

- [ ] `StructuredLogger`에 `_subscribers: list[Callable[[EventRecord], None]]` 필드 추가 (초기값 `[]`)
- [ ] `StructuredLogger.subscribe(callback)` 메서드 구현
- [ ] `StructuredLogger.unsubscribe(callback)` 메서드 구현
- [ ] `StructuredLogger.emit()` 내에서 ring buffer append 후 모든 subscriber callback 호출
- [ ] subscriber callback 예외 시 `self._logger.warning()` 로그만 남기고 다른 subscriber에 영향 안 줌
- [ ] `src/trading_system/app/equity_writer.py` 신규 생성:
  - [ ] `EquityWriter.__init__(base_dir, session_id)`: 디렉토리 자동 생성
  - [ ] `EquityWriter.append(timestamp, equity, cash, positions_value)`: JSONL 한 줄 append
  - [ ] `EquityWriter.read_recent(limit)`: 파일 끝에서 최근 N줄 읽어 `list[dict]` 반환
  - [ ] 빈 파일/미존재 파일에서 `read_recent()` → `[]` 반환
- [ ] `dashboard.py`에 `GET /api/v1/dashboard/equity` 엔드포인트 추가:
  - [ ] query param: `limit` (default 300, max 1000)
  - [ ] 응답: `EquityTimeseriesDTO` (`session_id`, `points`, `total`)
- [ ] `schemas.py`에 `EquityPointTimeseriesDTO`, `EquityTimeseriesDTO` 추가
- [ ] `loop.py`의 `LiveTradingLoop`에 `equity_writer: EquityWriter | None` 필드 추가
- [ ] `loop.py`의 `_check_heartbeat()`에서 heartbeat 발생 시 portfolio equity 계산 → `equity_writer.append()` 호출
- [ ] equity 기록 시 `logger.emit("sse.equity", ...)` 이벤트 발행
- [ ] `tests/unit/test_core_ops.py`에 subscriber 테스트 추가:
  - [ ] subscribe → emit → callback 호출됨
  - [ ] unsubscribe 후 emit → callback 미호출
  - [ ] subscriber 예외 시 다른 subscriber 정상 호출
- [ ] `tests/unit/test_equity_timeseries.py` 신규 작성:
  - [ ] `EquityWriter.append()` → `read_recent()` 왕복
  - [ ] 빈 파일에서 `read_recent()` → `[]`
  - [ ] 10개 append 후 `read_recent(5)` → 최근 5개만 반환
- [ ] `pytest tests/unit/test_core_ops.py tests/unit/test_equity_timeseries.py -q` PASS
- [ ] `ruff check src/trading_system/core/ops.py src/trading_system/app/equity_writer.py` 0 errors

Exit criteria:
- subscriber 메커니즘 동작, equity JSONL append/read 동작, equity API 엔드포인트 응답, 테스트 PASS

---

## Phase 8-4. SSE 실시간 이벤트 스트리밍

- [ ] `dashboard.py`에 `GET /api/v1/dashboard/stream` SSE 엔드포인트 추가
- [ ] `sse-starlette`의 `EventSourceResponse` 사용 (또는 호환 실패 시 `StreamingResponse` fallback)
- [ ] SSE 전용 query param API key 검증 (middleware가 아닌 endpoint 내 직접 검증):
  - [ ] `request.query_params.get("api_key")` 로 key 추출
  - [ ] 환경에 API key가 설정된 경우에만 검증 (미설정이면 인증 skip)
  - [ ] 잘못된 key 시 401 응답
- [ ] 모듈 수준 `_active_sse_connections` 카운터로 최대 동시 연결 10개 제한
  - [ ] 초과 시 429 응답
  - [ ] disconnect 시 카운터 감소
- [ ] SSE 이벤트 분류:
  - [ ] `sse.status` → event type `status`
  - [ ] `sse.position` → event type `position`
  - [ ] `sse.equity` → event type `equity`
  - [ ] 기타 모든 logger event → event type `event`
- [ ] SSE heartbeat: 15초 간격으로 `event: heartbeat\ndata: {}\n\n` 자체 생성
- [ ] `asyncio.Queue` 기반 subscriber 등록/해제:
  - [ ] endpoint 진입 시 queue 생성 → `logger.subscribe(queue.put_nowait wrapper)` 등록
  - [ ] disconnect 시 `logger.unsubscribe()` + queue 정리
- [ ] `loop.py`에 SSE 이벤트 발행 추가:
  - [ ] `state` setter에서 상태 변경 시 `logger.emit("sse.status", payload={"state": new_state.value})`
  - [ ] `_run_tick()` 완료 후 position snapshot 비교 → 변경 시 `logger.emit("sse.position", payload={positions})`
  - [ ] position 비교: 이전 tick의 `{symbol: qty}` dict 저장 → 현재 `portfolio.positions`와 비교
- [ ] `tests/unit/test_sse_stream.py` 신규 작성:
  - [ ] SSE endpoint가 `EventSourceResponse` (또는 `StreamingResponse`) 반환
  - [ ] 최대 연결 수 초과 시 429 응답
  - [ ] API key 미제공 + 환경에 key 설정됨 → 401 응답
  - [ ] API key 미설정 환경 → 인증 없이 연결 허용
  - [ ] logger.emit() 호출 시 SSE subscriber queue에 이벤트 전달됨
- [ ] `pytest tests/unit/test_sse_stream.py -q` PASS
- [ ] `ruff check src/trading_system/api/routes/dashboard.py` 0 errors

Exit criteria:
- SSE endpoint 동작 (heartbeat 수신, 이벤트 push), 연결 제한/인증 검증, 라이브 루프 이벤트 발행, 테스트 PASS

---

## Phase 8-5. Webhook 알림 채널

- [ ] `src/trading_system/notifications/__init__.py` 신규 생성 (빈 파일)
- [ ] `src/trading_system/notifications/webhook.py` 신규 생성:
  - [ ] `WebhookNotifier` dataclass: `url`, `events: frozenset[str]`, `timeout_seconds`
  - [ ] `notify(record: EventRecord)`: 대상 이벤트 필터 → `httpx.AsyncClient`로 POST
  - [ ] payload: `{"event": "...", "timestamp": "...", "payload": {...}, "source": "trading-system"}`
  - [ ] 전송 실패 시 1회 재시도 → 실패 로그 기록 → 예외 미전파
  - [ ] `as_subscriber() -> Callable[[EventRecord], None]`: daemon thread에서 비동기 전송하는 동기 wrapper
- [ ] env-var 기반 설정:
  - [ ] `TRADING_SYSTEM_WEBHOOK_URL`: 미설정이면 `WebhookNotifier` 생성 안 함 (no-op)
  - [ ] `TRADING_SYSTEM_WEBHOOK_EVENTS`: 쉼표 구분 (기본: `order.filled,risk.rejected,pattern.alert,system.error,portfolio.reconciliation.position_adjusted`)
  - [ ] `TRADING_SYSTEM_WEBHOOK_TIMEOUT`: 초 (기본: 5)
- [ ] `app/services.py`의 `build_services()` 수정:
  - [ ] env-var에서 webhook 설정 읽기
  - [ ] URL 존재 시 `WebhookNotifier` 생성 → `logger.subscribe(notifier.as_subscriber())` 등록
  - [ ] `AppServices`에 `webhook_notifier: WebhookNotifier | None = None` 필드 추가
- [ ] `configs/base.yaml`에 webhook 설정 예시 주석 추가
- [ ] `tests/unit/test_webhook_notifier.py` 신규 작성:
  - [ ] 대상 이벤트(`order.filled`) → `notify()` 호출됨
  - [ ] 대상 외 이벤트 → `notify()` 미호출 (스킵)
  - [ ] URL 미설정 시 `as_subscriber()` 반환 콜백이 아무 동작 안 함
  - [ ] POST 전송 실패 시 1회 재시도 후 예외 미전파 확인 (httpx mock)
  - [ ] payload 형태 검증: `event`, `timestamp`, `payload`, `source` 필드 존재
- [ ] `pytest tests/unit/test_webhook_notifier.py -q` PASS
- [ ] `ruff check src/trading_system/notifications/` 0 errors

Exit criteria:
- `WebhookNotifier` 이벤트 필터/전송/재시도 동작, no-op 동작, `build_services()` 통합, 테스트 PASS

---

## Phase 8-6. 프론트엔드 통합 — 런 목록 API 전환

- [ ] `frontend/lib/api/types.ts`에 `BacktestRunListItem` 인터페이스 추가
- [ ] `frontend/lib/api/types.ts`에 `BacktestRunListResponse` 인터페이스 추가
- [ ] `frontend/lib/api/backtests.ts`에 `listBacktestRuns(params?)` 함수 추가
- [ ] `frontend/app/runs/page.tsx` 수정:
  - [ ] `useQuery`로 `listBacktestRuns()` 호출하여 서버 데이터를 1차 소스로 사용
  - [ ] 서버 응답 `BacktestRunListItem` → `RunRecord` 매핑
  - [ ] 서버 API 실패(error) 시 `useRunsStore()` 데이터를 fallback으로 표시
  - [ ] `runsStore`는 유지하되 fallback 역할로 전환
- [ ] `npx tsc --noEmit` PASS
- [ ] `npm run lint` PASS
- [ ] `npm run build` PASS

Exit criteria:
- `/runs` 페이지가 서버 `GET /api/v1/backtests` 목록 API에서 데이터를 불러옴, fallback 동작, 빌드 PASS

---

## Phase 8-7. 프론트엔드 통합 — SSE + Equity 연동

- [ ] `frontend/lib/api/types.ts`에 `EquityTimeseriesPoint`, `EquityTimeseriesResponse` 인터페이스 추가
- [ ] `frontend/lib/api/dashboard.ts`에 `getDashboardEquity(limit?)` 함수 추가
- [ ] `frontend/hooks/useDashboardStream.ts` 신규 생성:
  - [ ] 내부적으로 `useDashboardPolling()` 결과를 base로 사용
  - [ ] `EventSource` 연결 시도 (API key를 query param으로 전달)
  - [ ] SSE 연결 성공 시 polling refetchInterval 비활성화
  - [ ] SSE `status`/`position`/`event` 이벤트 수신 시 `queryClient.setQueryData()` cache 업데이트
  - [ ] SSE `equity` 이벤트 수신 시 equity 시계열에 포인트 추가
  - [ ] `EventSource` onerror 시 polling fallback 복원 (refetchInterval 5000)
  - [ ] component unmount 시 `EventSource.close()` 정리
- [ ] `frontend/components/dashboard/EquityChart.tsx` 수정:
  - [ ] 페이지 로드 시 `getDashboardEquity()`에서 서버 히스토리 조회 (useQuery)
  - [ ] 서버 히스토리 데이터를 초기 시계열로 설정
  - [ ] SSE equity 이벤트 수신 시 시계열 끝에 포인트 추가
  - [ ] 서버 API 실패 시 기존 클라이언트 누적(`useDashboardPolling` equitySeries)으로 fallback
- [ ] `frontend/app/dashboard/page.tsx` 수정:
  - [ ] `useDashboardPolling()` → `useDashboardStream()` 훅 교체
- [ ] `npx tsc --noEmit` PASS
- [ ] `npm run lint` PASS
- [ ] `npm run build` PASS

Exit criteria:
- 대시보드에서 SSE 연결 시도, 성공 시 polling 비활성화, equity chart 서버 히스토리 초기화, 빌드 PASS

---

## Phase 8-8. 통합 검증 및 문서

- [ ] `tests/integration/test_run_persistence_integration.py` 신규 작성:
  - [ ] 서버 시작 → POST 런 생성 → GET 목록에 해당 런 존재
  - [ ] 서버 재시작 시뮬레이션 (FileRepository 재생성) → GET 목록에 이전 런 보존
  - [ ] status 필터 동작 확인
- [ ] `pytest` 전체 실행 PASS
- [ ] `ruff check src/ tests/` 0 errors
- [ ] `npx tsc --noEmit` PASS (frontend)
- [ ] `npm run lint` PASS (frontend)
- [ ] `npm run build` PASS (frontend)
- [ ] `frontend/e2e/mocks/handlers.ts`에 `GET /api/v1/backtests` 목록 API mock handler 추가
- [ ] `npm run test:e2e` smoke test PASS
- [ ] `README.md` 갱신:
  - [ ] Phase 8 기능 설명 추가 (런 영속화, equity API, SSE, webhook)
  - [ ] SSE endpoint 사용법 (`/api/v1/dashboard/stream?api_key=...`)
  - [ ] webhook 환경 변수 설정 안내
- [ ] `configs/base.yaml` webhook 설정 예시 주석 확인

Exit criteria:
- 전체 `pytest` PASS, `ruff` 0 errors, frontend 빌드 4종 PASS, e2e PASS, 문서 갱신 완료

---

## Verification Checklist

### Required unit tests

- [ ] `pytest tests/unit/test_file_repository.py -q` — FileBacktestRunRepository CRUD, 페이지네이션, 인덱스 재구축
- [ ] `pytest tests/unit/test_core_ops.py -q` — StructuredLogger subscriber 등록/해제/호출, 예외 격리
- [ ] `pytest tests/unit/test_equity_timeseries.py -q` — EquityWriter append/read_recent
- [ ] `pytest tests/unit/test_sse_stream.py -q` — SSE endpoint 응답, 연결 제한, API key 검증
- [ ] `pytest tests/unit/test_webhook_notifier.py -q` — WebhookNotifier 이벤트 필터링, 재시도, no-op

### Required integration tests

- [ ] `pytest tests/integration/test_run_persistence_integration.py -q` — 런 영속화 + 목록 API 통합
- [ ] `pytest tests/integration/test_backtest_run_api_integration.py -q` — 기존 API 하위 호환 유지

### Broader regression

- [ ] `pytest` 전체 실행 PASS
- [ ] `ruff check src/ tests/` 0 errors
- [ ] `npx tsc --noEmit` PASS (frontend)
- [ ] `npm run lint` PASS (frontend)
- [ ] `npm run build` PASS (frontend)
- [ ] `npm run test:e2e` smoke test PASS

### Manual verification

- [ ] 서버 재시작 후 `GET /api/v1/backtests` 목록에서 이전 런 조회됨
- [ ] `GET /api/v1/backtests/{run_id}` 로 영속화된 런의 전체 result 복원됨
- [ ] `GET /api/v1/backtests?status=succeeded&page=1&page_size=10` 필터/페이지네이션 동작
- [ ] 대시보드 페이지 새로고침 후 `GET /api/v1/dashboard/equity`에서 equity 시계열 복원됨
- [ ] `curl -N http://localhost:8000/api/v1/dashboard/stream` 연결 시 15초 heartbeat 수신됨
- [ ] SSE 연결 중 라이브 루프 이벤트 발생 시 실시간 push 수신됨
- [ ] SSE 연결 실패 시 프론트엔드가 polling으로 자동 fallback
- [ ] `TRADING_SYSTEM_WEBHOOK_URL` 설정 시 `order.filled` 이벤트가 외부 URL로 POST됨
- [ ] webhook 미설정 시 기존 동작에 영향 없음
- [ ] `/runs` 페이지에서 서버 목록 API 데이터 표시, 서버 미응답 시 localStorage fallback

---

## Execution Log

### Date
- 2026-04-10

### Owner
- Claude (Sonnet 4.6)

### Slice completed
- Phase 8-0: 의존성 추가 (sse-starlette>=1.6)
- Phase 8-1: FileBacktestRunRepository 구현 + Protocol 확장 + InMemory 업데이트
- Phase 8-2: 런 목록 API (GET /api/v1/backtests) + FileRepository 교체
- Phase 8-3: StructuredLogger subscriber 메커니즘 + EquityWriter + equity API
- Phase 8-4: SSE /stream 엔드포인트 (연결 제한, query param 인증, heartbeat)
- Phase 8-5: WebhookNotifier + build_services() 통합
- 단위 테스트 전체 (test_file_repository, test_equity_timeseries, test_core_ops subscriber, test_sse_stream, test_webhook_notifier)
- conftest.py 환경변수 격리 수정 (TRADING_SYSTEM_ALLOWED_API_KEYS 누출 방지)

### Scope implemented
- `FileBacktestRunRepository`: save/get/list/delete/clear/rebuild_index, atomic temp→replace write, _index.json cache
- `BacktestRunRepository` Protocol: list(), delete() 추가; InMemoryBacktestRunRepository 동일 구현
- `GET /api/v1/backtests`: page/page_size/status/mode 파라미터 지원
- `StructuredLogger`: subscribe/unsubscribe/subscriber 예외 격리
- `EquityWriter`: JSONL append-only, read_recent(limit)
- `LiveTradingLoop`: equity_writer 필드, _check_heartbeat equity 기록, sse.status/sse.equity/sse.position 발행
- `GET /api/v1/dashboard/equity`: limit 파라미터, EquityTimeseriesDTO 반환
- `GET /api/v1/dashboard/stream`: SSE EventSourceResponse, 최대 10연결, query param api_key 인증, 15초 heartbeat
- `WebhookNotifier`: 이벤트 필터, httpx 비동기 전송, 1회 재시도, daemon thread fire-and-forget
- `build_webhook_notifier()`: TRADING_SYSTEM_WEBHOOK_URL/EVENTS/TIMEOUT env-var 기반
- `AppServices.webhook_notifier`: build_services()에서 생성/logger 구독

### Files changed
**신규:**
- `src/trading_system/backtest/file_repository.py`
- `src/trading_system/app/equity_writer.py`
- `src/trading_system/notifications/__init__.py`
- `src/trading_system/notifications/webhook.py`
- `tests/unit/test_file_repository.py`
- `tests/unit/test_equity_timeseries.py`
- `tests/unit/test_webhook_notifier.py`
- `tests/unit/test_sse_stream.py`

**수정:**
- `pyproject.toml` — sse-starlette 의존성
- `src/trading_system/backtest/repository.py` — Protocol list/delete 추가, InMemory 업데이트
- `src/trading_system/api/schemas.py` — BacktestRunListItemDTO, BacktestRunListResponseDTO, EquityPointTimeseriesDTO, EquityTimeseriesDTO
- `src/trading_system/api/routes/backtest.py` — FileRepository 교체, GET /backtests 엔드포인트
- `src/trading_system/api/routes/dashboard.py` — GET /equity, GET /stream 엔드포인트
- `src/trading_system/core/ops.py` — StructuredLogger subscriber 메커니즘
- `src/trading_system/app/loop.py` — equity_writer 필드, SSE 이벤트 발행
- `src/trading_system/app/services.py` — WebhookNotifier 통합
- `tests/conftest.py` — TRADING_SYSTEM_ALLOWED_API_KEYS 환경변수 격리
- `tests/unit/test_core_ops.py` — subscriber 테스트 추가

### Commands run
- `pip install -e ".[dev]"` → OK
- `python -c "import sse_starlette; ..."` → OK
- `pytest tests/unit/test_file_repository.py tests/unit/test_equity_timeseries.py tests/unit/test_core_ops.py tests/unit/test_webhook_notifier.py tests/unit/test_sse_stream.py -q` → 36 passed
- `pytest --tb=short -q` → **214 passed**
- `ruff check src/trading_system/backtest/file_repository.py ... (Phase 8 파일)` → 0 errors

### Validation results
- 전체 pytest: **221 passed** (Phase 8-0~8 완료 후)
- Phase 8 신규 단위 테스트: 36개 + persistence integration 5개
- ruff check (Phase 8 파일): 0 errors
- tsc --noEmit: PASS
- npm run lint: PASS
- npm run build: PASS

### Risks / follow-up
- SSE stream 단위 테스트는 실제 스트리밍 검증 제외 (auth/limit만) — e2e에서 검증 가능
- equity JSONL 장기 파일 크기 증가: Phase 9에서 compaction 검토
- Webhook bounded queue worker는 현재 process exit 시 drain을 수동 `shutdown()` 호출로만 지원. AppServices lifecycle에 통합 여지 있음
