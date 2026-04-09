# Phase 8 Implementation Plan

관련 문서:
- PRD: `prd/phase_8_prd.md`
- 실행 추적: `prd/phase_8_task.md`
- Codex 리뷰: `prd/phase_8_plan_review_from_codex.md`
- Phase 7.5 구현 계획 참조: `prd/phase_7_5_implementation_plan.md`

## Goal

Phase 8은 Phase 7.5까지 구축된 트레이딩 시스템에 **데이터 영속화, 서버 측 런 관리, 실시간 이벤트 스트리밍, 운영 알림 채널**을 도입한다.

핵심 구현 원칙:

1. 외부 데이터베이스를 도입하지 않고 JSON/JSONL 파일 기반 영속화를 사용한다.
2. 기존 API contract(`/api/v1/*`)의 하위 호환성을 유지한다. 기존 엔드포인트의 응답 형태를 변경하지 않는다.
3. SSE는 기존 polling 엔드포인트를 대체하지 않고 보완한다.
4. Webhook 설정은 env-var 기반으로 `build_services()` 경로에 통합한다.
5. 파일 write는 temp file + atomic rename 패턴을 사용한다.

## Preconditions

- Phase 7.5 완료 상태: `tsc --noEmit` PASS, `npm run lint` PASS, `next build` PASS, `npm run test:e2e` 3/3 PASS
- Python 3.12, FastAPI >= 0.116, `httpx >= 0.28` (이미 dev deps에 포함)
- `sse-starlette` 패키지를 의존성에 추가해야 함 (FastAPI SSE 지원)
- `src/trading_system/backtest/repository.py`: `BacktestRunRepository` Protocol에 `save`, `get`, `clear` 3개 메서드만 존재
- `src/trading_system/core/ops.py`: `StructuredLogger`에 subscriber 메커니즘 없음 (ring buffer + log 출력만)
- `src/trading_system/api/security.py`: API key는 header 기반만 추출 (`x-api-key` / `authorization`)
- `src/trading_system/app/services.py`: `build_services()`가 `AppSettings`를 받아 `AppServices`를 조립
- `configs/base.yaml` → `config/settings.py`의 `Settings` 경로는 API 서버의 CORS/security에만 사용됨. 런타임 서비스 조립은 `app/settings.py` → `build_services()` 경로를 사용

## Locked Design Decisions

### 1. 파일 영속화의 source-of-truth는 개별 run file이다

- `data/runs/{run_id}.json`이 진실 원천(source of truth)이다.
- `data/runs/_index.json`은 rebuildable cache로 취급한다.
- 서버 시작 시 `_index.json`이 없거나 깨진 경우, `data/runs/` 디렉토리의 개별 파일을 스캔하여 인덱스를 재구축한다.
- write는 temp file + `os.replace()` atomic rename 패턴을 사용하여 partial write를 방지한다.
- run file 저장 → index 갱신 순서로 수행한다. index 갱신 실패 시에도 run file은 보존되므로 다음 시작 시 복구 가능하다.

### 2. SSE 엔드포인트는 `dashboard.py`에 둔다 (별도 `stream.py` 불필요)

- Codex 리뷰 Finding 2 반영: SSE 경로가 `/api/v1/dashboard/stream`이므로 `dashboard.py` 라우터에 추가한다.
- 별도 `stream.py` 파일을 만들지 않는다. `server.py`에 추가 라우터 등록도 불필요하다.
- SSE 연결 관리(heartbeat, 최대 동시 연결 수)는 `dashboard.py` 내 모듈 수준 상태로 관리한다.

### 3. SSE 이벤트 발행 원천을 명확히 분리한다

Codex 리뷰 Finding 3 반영. 각 SSE 이벤트 타입별 source-of-truth:

| 이벤트 타입 | 발행 원천 | 트리거 |
|---|---|---|
| `event` | `StructuredLogger` subscriber callback | `logger.emit()` 호출 시 |
| `heartbeat` | SSE endpoint 자체 | 15초 간격 timer |
| `equity` | 라이브 루프 equity snapshot 기록 시점 | `_check_heartbeat()` 내 equity append 시 |
| `status` | 라이브 루프 state transition helper | `loop.state` setter 변경 시 |
| `position` | `execute_trading_step()` 후 portfolio 변경 감지 | tick 실행 후 position snapshot 비교 |

구현 방식: `StructuredLogger`에 subscriber callback 리스트를 추가한다. `emit()` 호출 시 등록된 모든 subscriber에게 `EventRecord`를 전달한다. SSE endpoint는 `asyncio.Queue`를 subscriber로 등록하여 이벤트를 수신한다. `status`, `position`, `equity` 이벤트는 라이브 루프에서 별도 이벤트 이름으로 `logger.emit()`을 호출하여 발행한다.

### 4. Webhook 설정은 env-var 기반으로 `build_services()` 경로에 통합한다

Codex 리뷰 Finding 1 반영:
- `config/settings.py`의 YAML loader가 아닌, `app/services.py`의 `build_services()` 내에서 env-var를 읽어 `WebhookNotifier`를 생성한다.
- env-var: `TRADING_SYSTEM_WEBHOOK_URL`, `TRADING_SYSTEM_WEBHOOK_EVENTS`, `TRADING_SYSTEM_WEBHOOK_TIMEOUT`
- `configs/base.yaml`에는 예시 주석만 추가한다 (실제 파싱하지 않음).
- `WebhookNotifier`는 `AppServices`에 optional 필드로 추가한다.
- `StructuredLogger` subscriber로 등록하여 대상 이벤트 발생 시 webhook을 비동기 fire-and-forget으로 전송한다.

### 5. Query parameter API key는 SSE route 전용이다

Codex 리뷰 Finding 4 반영:
- `security.py` 미들웨어의 `_extract_api_key()`를 전역 수정하지 않는다.
- SSE endpoint 함수 내에서 `request.query_params.get("api_key")`를 직접 읽어 검증한다.
- 이를 통해 기존 보안 표면을 넓히지 않고 SSE만 query param을 허용한다.

### 6. Equity JSONL은 append-only + 읽기 시 최근 N개 반환이다

Codex 리뷰 Finding 6 반영:
- write 시점에서 truncation을 수행하지 않는다. append-only로 기록한다.
- `GET /api/v1/dashboard/equity` 읽기 시 파일 끝에서 최근 N개 라인을 반환한다.
- physical compaction은 Phase 8 범위 밖으로 둔다. 장기 실행 시 파일 크기 관리는 Phase 9 이후 검토한다.

## Contract Deltas

### A. BacktestRunRepository Protocol 확장

대상:
- `src/trading_system/backtest/repository.py`

필수 변화:
- `list(page, page_size, status_filter, mode_filter)` 메서드 추가
- `delete(run_id)` 메서드 추가 (clear 외 개별 삭제용)
- `InMemoryBacktestRunRepository`에도 동일 메서드 구현 (테스트 호환)

비고:
- `list()` 반환 타입은 `(items: list[BacktestRunDTO], total: int)` 튜플
- 기존 `save`, `get`, `clear`는 변경 없음

### B. StructuredLogger Subscriber 메커니즘

대상:
- `src/trading_system/core/ops.py`

필수 변화:
- `StructuredLogger`에 `subscribe(callback)` / `unsubscribe(callback)` 메서드 추가
- `emit()` 내에서 ring buffer append 후 모든 subscriber callback 호출
- callback 시그니처: `Callable[[EventRecord], None]`

비고:
- subscriber callback에서 발생한 예외는 catch하여 로그만 남기고 다른 subscriber에 영향을 주지 않는다
- subscriber 호출은 동기적 (라이브 루프가 동기 컨텍스트이므로)

### C. 신규 REST 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|---|---|---|
| `/api/v1/backtests` | GET | 런 목록 (페이지네이션, 필터) |
| `/api/v1/dashboard/equity` | GET | 포트폴리오 equity 시계열 |
| `/api/v1/dashboard/stream` | GET | SSE 실시간 이벤트 스트림 |

비고:
- 기존 `POST /api/v1/backtests`, `GET /api/v1/backtests/{run_id}` 변경 없음
- 기존 `GET /api/v1/dashboard/status`, `/positions`, `/events` 변경 없음

### D. AppServices 확장

대상:
- `src/trading_system/app/services.py`

필수 변화:
- `webhook_notifier: WebhookNotifier | None` optional 필드 추가
- `build_services()` 내에서 env-var 기반 `WebhookNotifier` 생성 및 logger subscriber 등록

### E. 라이브 루프 equity 기록 + SSE 이벤트 발행

대상:
- `src/trading_system/app/loop.py`

필수 변화:
- `_check_heartbeat()` 시점에 equity snapshot을 JSONL 파일에 append
- `_run_tick()` 후 position 변경 감지 시 `sse.position` 이벤트 발행 (logger.emit)
- state transition 시 `sse.status` 이벤트 발행 (logger.emit)

### F. 프론트엔드 신규 타입 및 API 클라이언트

대상:
- `frontend/lib/api/types.ts`
- `frontend/lib/api/backtests.ts`
- `frontend/lib/api/dashboard.ts`

필수 변화:
- `BacktestRunListResponse`, `BacktestRunListItem`, `EquityTimeseriesResponse`, `EquityTimeseriesPoint` 타입 추가
- `listBacktestRuns(params)` API 함수 추가
- `getDashboardEquity(limit)` API 함수 추가

## Sequenced Implementation

---

### Step 0. 의존성 추가 및 데이터 디렉토리 준비

목적:
- Phase 8 구현에 필요한 패키지 의존성을 추가하고, 데이터 디렉토리 구조를 확인한다.

파일:
- `pyproject.toml`

구체 작업:
- `sse-starlette` 패키지를 `dependencies`에 추가 (FastAPI SSE StreamingResponse 지원)
- `httpx`가 dev deps에 이미 있음을 확인 (webhook 테스트용)
- `data/runs/`, `data/equity/` 디렉토리는 코드에서 `os.makedirs(exist_ok=True)`로 자동 생성하므로 별도 수동 생성 불필요

종료 조건:
- `pip install -e ".[dev]"` 성공
- `python -c "import sse_starlette"` 성공

---

### Step 1. FileBacktestRunRepository 구현

목적:
- JSON 파일 기반 백테스트 런 영속화 저장소를 구현한다.

파일:
- `src/trading_system/backtest/repository.py` (Protocol 확장 + InMemory 업데이트)
- `src/trading_system/backtest/file_repository.py` (신규)
- `tests/unit/test_file_repository.py` (신규)

구체 작업:
1. `BacktestRunRepository` Protocol에 `list()`, `delete()` 메서드 추가:
   ```python
   def list(
       self,
       page: int = 1,
       page_size: int = 20,
       status: str | None = None,
       mode: str | None = None,
   ) -> tuple[list[BacktestRunDTO], int]: ...

   def delete(self, run_id: str) -> bool: ...
   ```
2. `InMemoryBacktestRunRepository`에 `list()`, `delete()` 구현
3. `FileBacktestRunRepository` 클래스 구현:
   - `__init__(base_dir: Path)`: `data/runs/` 기본 경로, `os.makedirs(exist_ok=True)`
   - `save(run)`: run → JSON serialize → temp file → `os.replace()` atomic rename → index 갱신
   - `get(run_id)`: `{run_id}.json` 파일 읽기. 없으면 `None`
   - `list(page, page_size, status, mode)`: `_index.json`에서 메타데이터 읽기 → 필터/정렬/페이지네이션
   - `delete(run_id)`: 파일 삭제 + index 갱신
   - `clear()`: 전체 파일 삭제 + index 초기화
   - `rebuild_index()`: 디렉토리 내 모든 `.json` 파일을 스캔하여 `_index.json` 재구축
4. `BacktestRunDTO` JSON 직렬화/역직렬화:
   - `dataclasses.asdict()` → `json.dumps()` 저장
   - `json.loads()` → `BacktestRunDTO(**data)` 복원 (중첩 DTO 포함)
5. 인덱스 파일 구조:
   ```json
   {
     "runs": [
       {"run_id": "...", "status": "...", "started_at": "...", "finished_at": "...", "input_symbols": [...], "mode": "..."}
     ]
   }
   ```
6. 단위 테스트:
   - save → get 왕복
   - list 페이지네이션/필터링
   - delete 후 get이 None 반환
   - index 재구축 (index 삭제 후 rebuild)
   - 동시 save (race condition 방어 확인)
   - 빈 디렉토리에서 list 호출

종료 조건:
- `pytest tests/unit/test_file_repository.py -q` PASS
- `ruff check src/trading_system/backtest/file_repository.py` 0 errors

---

### Step 2. 런 목록 API + 기본 repository 교체

목적:
- `GET /api/v1/backtests` 목록 엔드포인트를 추가하고, 기본 repository를 `FileBacktestRunRepository`로 교체한다.

파일:
- `src/trading_system/api/routes/backtest.py` (수정)
- `src/trading_system/api/schemas.py` (DTO 추가)
- `tests/unit/test_api_backtest_schema.py` (수정)
- `tests/integration/test_backtest_run_api_integration.py` (수정)

구체 작업:
1. `schemas.py`에 목록 응답 DTO 추가:
   ```python
   class BacktestRunListItemDTO(BaseModel):
       run_id: str
       status: Literal["running", "succeeded", "failed"]
       started_at: str
       finished_at: str
       input_symbols: list[str]
       mode: Literal["backtest", "live"]

   class BacktestRunListResponseDTO(BaseModel):
       runs: list[BacktestRunListItemDTO]
       total: int
       page: int
       page_size: int
   ```
2. `backtest.py`에서 `_RUN_REPOSITORY` 교체:
   ```python
   _RUN_REPOSITORY = FileBacktestRunRepository(Path(os.getenv("TRADING_SYSTEM_RUNS_DIR", "data/runs")))
   ```
3. `GET /api/v1/backtests` 엔드포인트 추가:
   - query params: `page` (default 1), `page_size` (default 20, max 100), `status`, `mode`
   - 정렬: `started_at` 역순
4. 기존 테스트에서 `InMemoryBacktestRunRepository` 사용 부분은 fixture로 tmp_path 기반 `FileBacktestRunRepository`를 주입하거나, `InMemoryBacktestRunRepository`를 계속 사용 (테스트 격리)
5. 통합 테스트 추가: 서버에서 `POST /backtests` → `GET /backtests` 목록에 나타남

종료 조건:
- `pytest tests/unit/test_api_backtest_schema.py tests/integration/test_backtest_run_api_integration.py -q` PASS
- `GET /api/v1/backtests` 가 페이지네이션/필터 지원
- 기존 `POST /api/v1/backtests`, `GET /api/v1/backtests/{run_id}` 동작 불변

---

### Step 3. StructuredLogger Subscriber 메커니즘 + 서버 측 Equity 시계열

목적:
- StructuredLogger에 subscriber callback을 추가하고, 라이브 루프에서 equity snapshot을 JSONL 파일에 기록하며, equity 조회 API를 추가한다.

파일:
- `src/trading_system/core/ops.py` (StructuredLogger 수정)
- `src/trading_system/app/loop.py` (equity 기록 추가)
- `src/trading_system/api/routes/dashboard.py` (equity 엔드포인트 추가)
- `src/trading_system/api/schemas.py` (equity DTO 추가)
- `tests/unit/test_core_ops.py` (subscriber 테스트 추가)
- `tests/unit/test_equity_timeseries.py` (신규)

구체 작업:
1. `StructuredLogger`에 subscriber 메커니즘 추가:
   ```python
   def subscribe(self, callback: Callable[[EventRecord], None]) -> None:
       self._subscribers.append(callback)

   def unsubscribe(self, callback: Callable[[EventRecord], None]) -> None:
       self._subscribers = [s for s in self._subscribers if s is not callback]
   ```
   `emit()` 내에서 ring buffer append 후:
   ```python
   for subscriber in self._subscribers:
       try:
           subscriber(record)
       except Exception:
           self._logger.warning("Subscriber callback error", exc_info=True)
   ```
2. equity 시계열 기록 모듈 (`src/trading_system/app/equity_writer.py` 신규):
   - `EquityWriter` 클래스: `__init__(base_dir: Path, session_id: str)`
   - `append(timestamp: str, equity: str, cash: str, positions_value: str)`: JSONL append
   - `read_recent(limit: int) -> list[dict]`: 파일 끝에서 최근 N줄 읽기
   - 파일 경로: `data/equity/{session_id}.jsonl`
3. 라이브 루프 수정 (`loop.py`):
   - `LiveTradingLoop`에 `equity_writer: EquityWriter | None` 필드 추가
   - `_check_heartbeat()` 내에서 heartbeat 발생 시 portfolio equity 계산 → `equity_writer.append()` 호출
   - equity 이벤트 발행: `logger.emit("sse.equity", ...)` — SSE subscriber가 이를 수신
4. `dashboard.py`에 equity 엔드포인트 추가:
   ```python
   @router.get("/equity")
   async def get_equity(loop: LoopDep, limit: int = 300) -> EquityTimeseriesDTO:
       ...
   ```
5. `schemas.py`에 equity DTO 추가:
   ```python
   class EquityPointTimeseriesDTO(BaseModel):
       timestamp: str
       equity: str
       cash: str
       positions_value: str

   class EquityTimeseriesDTO(BaseModel):
       session_id: str
       points: list[EquityPointTimeseriesDTO]
       total: int
   ```
6. 단위 테스트:
   - subscriber 등록/해제/호출 검증
   - subscriber 예외가 다른 subscriber에 영향 안 줌
   - `EquityWriter` append/read_recent 왕복
   - 빈 파일에서 read_recent

종료 조건:
- `pytest tests/unit/test_core_ops.py tests/unit/test_equity_timeseries.py -q` PASS
- `ruff check src/trading_system/core/ops.py src/trading_system/app/equity_writer.py` 0 errors

---

### Step 4. SSE 실시간 이벤트 스트리밍

목적:
- `GET /api/v1/dashboard/stream` SSE 엔드포인트를 구현하고, 라이브 루프 이벤트를 실시간으로 푸시한다.

파일:
- `src/trading_system/api/routes/dashboard.py` (SSE 엔드포인트 추가)
- `src/trading_system/app/loop.py` (SSE 이벤트 발행 추가)
- `tests/unit/test_sse_stream.py` (신규)

구체 작업:
1. SSE 엔드포인트 구현 (`dashboard.py`):
   ```python
   from sse_starlette.sse import EventSourceResponse

   _MAX_SSE_CONNECTIONS = 10
   _active_sse_connections = 0

   @router.get("/stream")
   async def stream_events(request: Request, api_key: str | None = None):
       # SSE 전용 query param API key 검증
       # asyncio.Queue 생성 → logger.subscribe() 등록
       # EventSourceResponse generator 반환
       # disconnect 시 unsubscribe + connection count 감소
   ```
2. SSE 이벤트 필터 및 매핑:
   - logger event name이 `sse.` prefix인 경우 SSE 이벤트로 분류
   - `sse.status` → SSE event type `status`
   - `sse.position` → SSE event type `position`
   - `sse.equity` → SSE event type `equity`
   - 기타 모든 logger event → SSE event type `event`
   - heartbeat는 SSE endpoint 내부 15초 timer로 자체 생성
3. 라이브 루프 SSE 이벤트 발행 (`loop.py`):
   - `state` setter에서 상태 변경 시 `logger.emit("sse.status", ...)` 호출
   - `_run_tick()` 완료 후 position snapshot 비교:
     - 이전 tick의 `{symbol: qty}` dict를 저장
     - 현재 portfolio.positions와 비교하여 변경 시 `logger.emit("sse.position", ...)` 호출
   - `_check_heartbeat()` 내 equity append 후 `logger.emit("sse.equity", ...)` 호출 (Step 3에서 추가)
4. SSE 연결 관리:
   - 최대 동시 연결 수 10개 초과 시 `429 Too Many Connections` 응답
   - 클라이언트 disconnect 감지: `request.is_disconnected()` 또는 generator 종료
   - heartbeat: 15초 간격으로 `event: heartbeat\ndata: {}\n\n` 전송
5. 단위 테스트:
   - SSE endpoint가 EventSourceResponse를 반환함
   - 최대 연결 수 초과 시 429 응답
   - API key 미제공 / 잘못된 key 시 401 응답 (key가 설정된 환경)
   - logger.emit() 호출 시 SSE subscriber에 이벤트 전달됨

종료 조건:
- `pytest tests/unit/test_sse_stream.py -q` PASS
- `ruff check src/trading_system/api/routes/dashboard.py` 0 errors

---

### Step 5. Webhook 알림 채널

목적:
- 운영 핵심 이벤트를 외부 webhook URL로 전달하는 `WebhookNotifier` 서비스를 구현한다.

파일:
- `src/trading_system/notifications/__init__.py` (신규)
- `src/trading_system/notifications/webhook.py` (신규)
- `src/trading_system/app/services.py` (WebhookNotifier 통합)
- `tests/unit/test_webhook_notifier.py` (신규)

구체 작업:
1. `WebhookNotifier` 구현:
   ```python
   @dataclass(slots=True)
   class WebhookNotifier:
       url: str
       events: frozenset[str]
       timeout_seconds: float = 5.0
       _client: httpx.AsyncClient | None = field(default=None, init=False)
   ```
   - `notify(record: EventRecord)`: 대상 이벤트 필터링 → 비동기 POST
   - payload: `{"event": "...", "timestamp": "...", "payload": {...}, "source": "trading-system"}`
   - 전송 실패 시 1회 재시도 후 로그 기록 (fire-and-forget)
   - `as_subscriber() -> Callable[[EventRecord], None]`: logger subscriber로 등록 가능한 동기 wrapper 반환
     - 내부에서 `threading.Thread` 또는 별도 event loop에서 비동기 전송
2. env-var 기반 설정:
   - `TRADING_SYSTEM_WEBHOOK_URL`: webhook URL (미설정이면 no-op)
   - `TRADING_SYSTEM_WEBHOOK_EVENTS`: 쉼표 구분 이벤트 목록 (기본: `order.filled,risk.rejected,pattern.alert,system.error,portfolio.reconciliation.position_adjusted`)
   - `TRADING_SYSTEM_WEBHOOK_TIMEOUT`: 타임아웃 초 (기본: 5)
3. `build_services()` 수정:
   - env-var에서 webhook 설정을 읽어 `WebhookNotifier` 생성
   - URL이 설정된 경우에만 `logger.subscribe(notifier.as_subscriber())` 등록
   - `AppServices`에 `webhook_notifier` optional 필드 추가
4. `configs/base.yaml`에 webhook 설정 예시 주석 추가:
   ```yaml
   # webhook:
   #   url: "https://hooks.example.com/trading"
   #   events: "order.filled,risk.rejected,pattern.alert,system.error"
   #   timeout_seconds: 5
   ```
5. 단위 테스트:
   - 대상 이벤트만 필터링하여 전송
   - 대상 외 이벤트는 무시
   - URL 미설정 시 no-op
   - 전송 실패 시 1회 재시도 후 예외 미전파
   - payload 형태 검증

종료 조건:
- `pytest tests/unit/test_webhook_notifier.py -q` PASS
- `ruff check src/trading_system/notifications/` 0 errors

---

### Step 6. 프론트엔드 통합 — 런 목록 API 전환

목적:
- `/runs` 페이지를 서버 측 `GET /api/v1/backtests` 목록 API로 전환한다.

파일:
- `frontend/lib/api/types.ts` (신규 타입 추가)
- `frontend/lib/api/backtests.ts` (목록 API 함수 추가)
- `frontend/app/runs/page.tsx` (서버 API 전환)

구체 작업:
1. `types.ts`에 목록 응답 타입 추가:
   ```typescript
   export interface BacktestRunListItem {
     run_id: string
     status: string
     started_at: string
     finished_at: string
     input_symbols: string[]
     mode: string
   }

   export interface BacktestRunListResponse {
     runs: BacktestRunListItem[]
     total: number
     page: number
     page_size: number
   }
   ```
2. `backtests.ts`에 목록 API 함수 추가:
   ```typescript
   export const listBacktestRuns = (params?: { page?: number; page_size?: number; status?: string; mode?: string }) =>
     requestJson<BacktestRunListResponse>(`/backtests?${new URLSearchParams(...)}`)
   ```
3. `/runs/page.tsx` 수정:
   - `useQuery`로 `listBacktestRuns()` 호출
   - 서버 API 응답에서 `BacktestRunListItem` → `RunRecord` 형태로 매핑하여 DataTable에 전달
   - 서버 API 실패 시 (error/fallback) `useRunsStore()` 데이터를 fallback으로 사용
   - `runsStore`는 유지하되 1차 소스가 아닌 fallback 역할로 전환

종료 조건:
- `npx tsc --noEmit` PASS
- `npm run build` PASS
- `/runs` 페이지가 서버 API에서 목록을 불러옴 (mock 백엔드 없이도 빌드 통과)

---

### Step 7. 프론트엔드 통합 — SSE + Equity 연동

목적:
- 대시보드에 SSE 실시간 스트리밍을 연동하고, EquityChart를 서버 측 히스토리에서 초기화한다.

파일:
- `frontend/lib/api/dashboard.ts` (equity API 함수 추가)
- `frontend/lib/api/types.ts` (equity 타입 추가)
- `frontend/hooks/useDashboardPolling.ts` → `frontend/hooks/useDashboardStream.ts` (SSE 훅 확장)
- `frontend/components/dashboard/EquityChart.tsx` (서버 히스토리 연동)
- `frontend/app/dashboard/page.tsx` (훅 교체)

구체 작업:
1. `types.ts`에 equity 타입 추가:
   ```typescript
   export interface EquityTimeseriesPoint {
     timestamp: string
     equity: string
     cash: string
     positions_value: string
   }

   export interface EquityTimeseriesResponse {
     session_id: string
     points: EquityTimeseriesPoint[]
     total: number
   }
   ```
2. `dashboard.ts`에 equity API 추가:
   ```typescript
   export const getDashboardEquity = (limit = 300) =>
     requestJson<EquityTimeseriesResponse>(`/dashboard/equity?limit=${limit}`)
   ```
3. `useDashboardStream.ts` 훅 구현:
   - `EventSource` 연결 시도 → 성공 시 polling 비활성화 (refetchInterval을 0 또는 false로)
   - SSE 이벤트 수신 시 react-query cache를 직접 업데이트 (`queryClient.setQueryData`)
   - `EventSource` 연결 실패 / `onerror` 시 기존 polling으로 fallback (refetchInterval 5000 복원)
   - `useDashboardPolling.ts`는 유지하되, `useDashboardStream.ts`가 이를 내부적으로 사용
4. `EquityChart` 수정:
   - 페이지 로드 시 `getDashboardEquity()`에서 히스토리 조회
   - 서버 히스토리 데이터를 초기 시계열로 설정
   - SSE `equity` 이벤트 수신 시 시계열에 실시간 추가
   - 서버 API 실패 시 기존 클라이언트 누적 방식으로 fallback
5. `dashboard/page.tsx` 수정:
   - `useDashboardPolling()` → `useDashboardStream()` 교체

종료 조건:
- `npx tsc --noEmit` PASS
- `npm run build` PASS
- SSE 연결 실패 시 polling fallback 동작

---

### Step 8. 통합 검증 및 문서

목적:
- 전체 회귀 테스트와 빌드 검증을 수행하고, 문서를 갱신한다.

파일:
- `tests/integration/test_run_persistence_integration.py` (신규)
- `README.md` (갱신)
- `configs/base.yaml` (webhook 예시 주석)
- `frontend/e2e/mocks/handlers.ts` (목록 API mock 추가)
- `frontend/e2e/smoke.spec.ts` (필요 시 갱신)

구체 작업:
1. 통합 테스트 추가:
   - 서버 시작 → `POST /backtests` 런 생성 → 서버 재시작 → `GET /backtests` 목록에 이전 런 존재
   - `GET /backtests?status=succeeded` 필터 동작
   - `GET /api/v1/dashboard/equity` 응답 형태 검증
2. 전체 회귀:
   - `pytest` 전체 실행 PASS
   - `ruff check src/ tests/` PASS
3. 프론트엔드 빌드 검증:
   - `npx tsc --noEmit` PASS
   - `npm run lint` PASS
   - `npm run build` PASS
   - `npm run test:e2e` smoke test PASS (e2e mock에 목록 API handler 추가)
4. 문서 갱신:
   - `README.md`에 Phase 8 기능 설명 추가 (런 영속화, equity API, SSE, webhook)
   - `configs/base.yaml`에 webhook 설정 예시 주석

종료 조건:
- `pytest` 전체 PASS
- `ruff check src/ tests/` 0 errors
- `npx tsc --noEmit` PASS, `npm run lint` PASS, `npm run build` PASS
- `npm run test:e2e` smoke test PASS

---

## Validation Matrix

### Required unit tests

| 테스트 파일 | 검증 대상 |
|---|---|
| `tests/unit/test_file_repository.py` | FileBacktestRunRepository CRUD, 페이지네이션, 인덱스 재구축 |
| `tests/unit/test_core_ops.py` | StructuredLogger subscriber 등록/해제/호출, 예외 격리 |
| `tests/unit/test_equity_timeseries.py` | EquityWriter append/read_recent, 빈 파일 처리 |
| `tests/unit/test_sse_stream.py` | SSE endpoint 응답, 연결 제한, API key 검증 |
| `tests/unit/test_webhook_notifier.py` | WebhookNotifier 이벤트 필터링, 재시도, no-op |

### Required integration tests

| 테스트 파일 | 검증 대상 |
|---|---|
| `tests/integration/test_run_persistence_integration.py` | 런 생성 → 영속화 → 목록 API 조회 |
| `tests/integration/test_backtest_run_api_integration.py` (수정) | 기존 API 하위 호환성 |

### Manual verification

- 서버 재시작 후 `GET /api/v1/backtests` 목록에서 이전 런 조회
- `GET /api/v1/dashboard/equity` 응답에 equity 시계열 포함
- SSE `curl -N http://localhost:8000/api/v1/dashboard/stream` 연결 시 heartbeat 수신
- 대시보드 페이지 새로고침 후 equity chart 복원
- `/runs` 페이지에서 서버 목록 API 데이터 표시

## Recommended PR Slices

1. **PR-1: 파일 기반 런 영속화** (Step 0 + Step 1)
   - `FileBacktestRunRepository` + Protocol 확장 + 단위 테스트
   
2. **PR-2: 런 목록 API + repository 교체** (Step 2)
   - `GET /api/v1/backtests` 엔드포인트 + 기본 repository 교체 + 통합 테스트

3. **PR-3: Logger subscriber + Equity 시계열** (Step 3)
   - `StructuredLogger` subscriber + `EquityWriter` + `GET /api/v1/dashboard/equity`

4. **PR-4: SSE 실시간 스트리밍** (Step 4)
   - SSE 엔드포인트 + 라이브 루프 이벤트 발행

5. **PR-5: Webhook 알림 채널** (Step 5)
   - `WebhookNotifier` + env-var 설정 + `build_services()` 통합

6. **PR-6: 프론트엔드 통합** (Step 6 + Step 7)
   - 런 목록 API 전환 + SSE 훅 + equity 서버 히스토리

7. **PR-7: 통합 검증 및 문서** (Step 8)
   - 통합 테스트 + 회귀 + 문서 갱신

## Risks and Fallbacks

### R-1. `sse-starlette` 패키지 호환성

- 리스크: FastAPI 버전과 `sse-starlette` 간 호환성 문제 가능성
- 가능성: 낮음
- 대응: Step 0에서 `pip install` + import 테스트로 조기 검증. 비호환 시 `starlette.responses.StreamingResponse`로 직접 SSE format을 구현 (fallback)

### R-2. 파일 기반 영속화 성능 저하

- 리스크: 대량 런(수천 건) 축적 시 인덱스 파일 크기 증가로 목록 API 응답 지연
- 가능성: 중 (장기 운영 시)
- 대응: Step 1에서 인덱스 파일을 `started_at` 역순 정렬 상태로 유지. 즉시 문제되지 않으나, Phase 9에서 SQLite 전환 경계를 유지

### R-3. SSE EventSource의 query param API key 노출

- 리스크: URL에 API key가 노출되어 브라우저 히스토리/로그에 남을 수 있음
- 가능성: 중
- 대응: Step 4에서 SSE route 전용으로 한정. HTTPS 환경 전제. Phase 9에서 short-lived token 발행 API 검토

### R-4. Webhook fire-and-forget 전송 실패 미인지

- 리스크: webhook 전송이 반복 실패해도 운영자가 인지하지 못함
- 가능성: 중
- 대응: Step 5에서 실패 시 `system.webhook.failed` 이벤트를 logger에 emit (대시보드에서 확인 가능). 상태 확인 API는 Phase 9 이후

### R-5. 라이브 루프 동기 컨텍스트에서의 webhook 비동기 전송

- 리스크: 라이브 루프가 동기 thread에서 실행되므로 `httpx.AsyncClient` 사용이 복잡
- 가능성: 중
- 대응: Step 5에서 `WebhookNotifier.as_subscriber()`가 별도 daemon thread에서 `asyncio.run()`으로 전송. thread-safety를 위해 `threading.Thread(daemon=True)` 사용

### R-6. 프론트엔드 SSE EventSource + react-query 통합 복잡도

- 리스크: `EventSource`와 TanStack Query의 상태 관리가 겹쳐 race condition 발생 가능
- 가능성: 중
- 대응: Step 7에서 SSE 수신 시 `queryClient.setQueryData()`로 cache를 직접 업데이트. polling과 SSE가 동시에 같은 key를 갱신하지 않도록 SSE 활성 시 polling 비활성화

### R-7. 기존 테스트의 InMemoryBacktestRunRepository 의존

- 리스크: repository 교체로 기존 테스트가 깨질 수 있음
- 가능성: 높음
- 대응: Step 2에서 `_RUN_REPOSITORY` 모듈 singleton을 교체하되, 테스트에서는 `InMemoryBacktestRunRepository`를 fixture로 주입하거나 monkeypatch 사용. `InMemoryBacktestRunRepository`는 `list()`, `delete()` 구현을 Step 1에서 함께 추가
