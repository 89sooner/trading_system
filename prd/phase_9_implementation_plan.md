# Phase 9 Implementation Plan

관련 문서:
- PRD: `prd/phase_9_prd.md`
- 실행 추적: `prd/phase_9_task.md`
- Codex 리뷰: `prd/phase_9_plan_review_from_codex.md`
- Phase 8 구현 계획 참조: `prd/phase_8_implementation_plan.md`

## Goal

Phase 9는 Phase 8까지 구축된 트레이딩 시스템을 **Vercel(프론트엔드), Railway(FastAPI 백엔드), Supabase(PostgreSQL)** 에 배포하여 실제 운영 환경에서 사용 가능한 상태로 만든다.

핵심 구현 원칙:

1. 기존 `BacktestRunRepository` Protocol과 `EquityWriter` 인터페이스를 변경하지 않는다. 구현체만 추가한다.
2. `_RUN_REPOSITORY` 모듈 싱글턴을 env-aware factory로 교체한다 (`backtest.py` 수준).
3. `EquityWriterProtocol`에 `session_id` 속성을 포함한다.
4. 기존 security middleware의 CORS 처리를 유지한다. `CORSMiddleware`를 별도 추가하지 않는다.
5. 프론트엔드 env는 기존 `NEXT_PUBLIC_API_BASE_URL`을 유지하고, API key는 런타임 입력 방식을 유지한다.
6. `server.py`에 모듈 전역 `app = create_app()`을 추가하여 uvicorn 표준 형식을 지원한다.
7. 로컬 개발 환경은 `DATABASE_URL` 없이 기존 파일 기반으로 계속 동작한다.

## Preconditions

- Phase 8 완료 상태: pytest 221개 PASS, ruff 0 errors, frontend build PASS
- Supabase 계정 및 프로젝트 생성 완료 (수동)
- Railway 계정 및 프로젝트 생성 완료 (수동)
- Vercel 계정 및 프로젝트 생성 완료 (수동)
- GitHub 리포지토리에 연결된 상태

## Locked Design Decisions

### 1. psycopg3 동기 드라이버를 사용한다

- 현재 FastAPI 엔드포인트 핸들러는 동기(`def`) 방식이다. psycopg3 동기 드라이버(`psycopg[binary]`)를 사용하면 기존 코드 변경 없이 DB 호출이 가능하다.
- FastAPI가 동기 핸들러를 threadpool에서 실행하므로 이벤트 루프 블로킹 없이 동작한다.
- `DATABASE_URL` 형식: `postgresql://user:password@host:port/dbname` (Supabase Connection String).

### 2. `_RUN_REPOSITORY` 모듈 싱글턴을 env-aware factory로 교체한다

- Codex Finding 1 반영. `backtest.py`의 모듈 전역 `_RUN_REPOSITORY` 초기화를 factory 함수로 교체한다.
- `analytics.py`는 `from ...backtest import _RUN_REPOSITORY`로 임포트하므로 자동 교체된다.
- `build_services()` 경로에 repository를 추가하지 않는다 (기존 모듈 패턴 유지).

### 3. EquityWriter Protocol에 `session_id` 속성을 포함한다

- Codex Finding 2 반영. `dashboard.py`의 `GET /equity`가 `equity_writer.session_id`를 읽는다.
- Protocol: `session_id: str` 읽기 속성 + `append()` + `read_recent()`.
- 주입 경로는 `LiveTradingLoop.__init__`의 `equity_writer` 파라미터. `AppServices`에 추가하지 않는다.
- `session_id` 생성 정책은 기존 호출자 경로 유지 (변경 없음).

### 4. 기존 security middleware CORS를 유지한다

- Codex Finding 3 반영. `CORSMiddleware` 추가 없음.
- env-var: `TRADING_SYSTEM_CORS_ALLOW_ORIGINS` (기존 이름 유지).
- `configs/base.yaml` 기본값: `*` (기존 값 유지).
- Vercel URL은 env-var에 추가하면 자동 처리.
- `security.py` 코드 변경 없음.

### 5. 프론트엔드 env는 `NEXT_PUBLIC_API_BASE_URL`을 유지한다

- Codex Finding 4 반영. 값에 `/api/v1` 접미사 포함.
- API key: Zustand 스토어 런타임 입력 (env-var 도입 안 함).
- Vercel: `NEXT_PUBLIC_API_BASE_URL=https://my-backend.railway.app/api/v1` 설정.

### 6. `server.py`에 모듈 전역 `app`을 추가한다

- Codex Finding 5 반영. `create_app()` 팩토리 아래에 `app = create_app()` 추가.
- Dockerfile CMD: `uvicorn trading_system.api.server:app --host 0.0.0.0 --port ${PORT:-8000}`.

### 7. `.env.example`은 기존 파일을 확장한다

- Codex Finding 5 반영. 신규 생성이 아니라 `DATABASE_URL` 등을 기존 파일에 추가.

## Contract Deltas

### EquityWriter (equity_writer.py)

**기존**: `EquityWriter` 구체 클래스 (파일 기반, `session_id` property + `append` + `read_recent`)

**변경**:
```python
class EquityWriterProtocol(Protocol):
    @property
    def session_id(self) -> str: ...
    def append(self, timestamp: str, equity: str, cash: str, positions_value: str) -> None: ...
    def read_recent(self, limit: int = 300) -> list[dict]: ...

class FileEquityWriter:  # 기존 EquityWriter 내용 그대로
    ...

EquityWriter = FileEquityWriter  # 하위 호환 alias
```

### _RUN_REPOSITORY (api/routes/backtest.py)

**기존**:
```python
_RUN_REPOSITORY = FileBacktestRunRepository(
    Path(os.getenv("TRADING_SYSTEM_RUNS_DIR", "data/runs"))
)
```

**변경**:
```python
def _create_run_repository() -> BacktestRunRepository:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        from trading_system.backtest.supabase_repository import SupabaseBacktestRunRepository
        return SupabaseBacktestRunRepository(database_url)
    return FileBacktestRunRepository(
        Path(os.getenv("TRADING_SYSTEM_RUNS_DIR", "data/runs"))
    )

_RUN_REPOSITORY = _create_run_repository()
```

### server.py

**추가**:
```python
# 기존 create_app() 아래에 추가
app = create_app()
```

## Implementation Steps

---

### Step 9-0. 의존성 추가 + EquityWriter Protocol 분리

**목적**: psycopg3 의존성을 추가하고, `EquityWriter`를 Protocol로 분리하여 Supabase 구현체를 추가할 수 있는 경계를 만든다.

**파일**:
- `pyproject.toml`
- `src/trading_system/app/equity_writer.py`
- `src/trading_system/app/loop.py`

**작업 항목**:
1. `pyproject.toml`의 `dependencies`에 `psycopg[binary]>=3.1` 추가.
2. `equity_writer.py`에 `EquityWriterProtocol` Protocol 클래스 추가:
   - `session_id: str` 읽기 속성 (property)
   - `append(timestamp, equity, cash, positions_value) -> None`
   - `read_recent(limit: int = 300) -> list[dict]`
3. 기존 `EquityWriter` 클래스를 `FileEquityWriter`로 rename.
4. `EquityWriter = FileEquityWriter` alias 추가 (하위 호환).
5. `loop.py`의 `equity_writer: EquityWriter | None` 타입 힌트 확인. `EquityWriterProtocol | None`로 변경하거나, `FileEquityWriter` 기반 alias가 있으므로 기존 힌트 유지 가능 — 최소 변경 원칙에 따라 기존 import가 동작하면 유지.
6. `pip install -e ".[dev]"` 실행하여 psycopg 설치 확인.

**Exit criteria**:
- `python -c "import psycopg"` 성공
- `pytest --tb=short -q` PASS (기존 테스트 영향 없음)
- `ruff check src/trading_system/app/equity_writer.py src/trading_system/app/loop.py` 0 errors

---

### Step 9-1. SQL 마이그레이션 파일 작성

**목적**: Supabase PostgreSQL에 적용할 스키마 SQL을 준비한다.

**파일**:
- `scripts/migrations/001_create_backtest_runs.sql`
- `scripts/migrations/002_create_equity_snapshots.sql`

**작업 항목**:
1. `scripts/migrations/` 디렉토리 생성.
2. `001_create_backtest_runs.sql` 작성:
   ```sql
   CREATE TABLE IF NOT EXISTS backtest_runs (
       run_id      TEXT PRIMARY KEY,
       status      TEXT NOT NULL,
       started_at  TIMESTAMPTZ,
       finished_at TIMESTAMPTZ,
       input_symbols TEXT[] NOT NULL DEFAULT '{}',
       mode        TEXT NOT NULL DEFAULT 'backtest',
       result      JSONB,
       error       TEXT,
       created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
   );
   ```
3. `002_create_equity_snapshots.sql` 작성:
   ```sql
   CREATE TABLE IF NOT EXISTS equity_snapshots (
       id              BIGSERIAL PRIMARY KEY,
       session_id      TEXT NOT NULL,
       timestamp       TIMESTAMPTZ NOT NULL,
       equity          NUMERIC,
       cash            NUMERIC,
       positions_value NUMERIC,
       created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
   );
   CREATE INDEX IF NOT EXISTS idx_equity_snapshots_session_ts
       ON equity_snapshots (session_id, timestamp DESC);
   ```

**Exit criteria**:
- SQL 파일 문법 오류 없음
- `scripts/migrations/` 에 2개 파일 존재

---

### Step 9-2. SupabaseBacktestRunRepository 구현

**목적**: `BacktestRunRepository` Protocol을 Supabase PostgreSQL 기반으로 구현한다.

**파일**:
- `src/trading_system/backtest/supabase_repository.py` (신규)
- `tests/unit/test_supabase_repository.py` (신규)

**작업 항목**:
1. `supabase_repository.py` 생성:
   - `SupabaseBacktestRunRepository(database_url: str)` 클래스.
   - `__init__`: `psycopg.connect(database_url, autocommit=True)` 커넥션 생성.
   - `save(run)`: `INSERT INTO backtest_runs ... ON CONFLICT (run_id) DO UPDATE SET ...`. `result` 필드는 `json.dumps(dataclasses.asdict(run.result))` 로 직렬화.
   - `get(run_id)`: `SELECT * FROM backtest_runs WHERE run_id = %s`. `_deserialize_run(row)` 헬퍼로 `BacktestRunDTO` 복원. 없으면 `None`.
   - `list(page, page_size, status, mode)`: 필터 조건 동적 구성, `ORDER BY started_at DESC NULLS LAST`, `LIMIT %s OFFSET %s`. 별도 `COUNT(*)` 쿼리로 total 반환.
   - `delete(run_id)`: `DELETE FROM backtest_runs WHERE run_id = %s`. `cursor.rowcount` 로 존재 여부 확인.
   - `clear()`: `DELETE FROM backtest_runs`.
   - `rebuild_index()`: no-op (로그만 기록).
   - `_deserialize_run(row)`: DB row → `BacktestRunDTO` 역직렬화 헬퍼. `result` JSONB → 중첩 DTO 복원은 `FileBacktestRunRepository`의 역직렬화 로직을 참조하거나 공통 헬퍼로 추출.
2. `test_supabase_repository.py` 작성 (mock 기반):
   - psycopg 커넥션/커서를 `unittest.mock.MagicMock`으로 mock.
   - `save()` 호출 시 execute에 upsert SQL + 올바른 파라미터가 전달됨.
   - `get()` mock row 반환 시 `BacktestRunDTO` 복원됨.
   - `get()` 결과 없음 시 `None` 반환.
   - `list()` status/mode 필터 파라미터 전달 확인.
   - `delete()` rowcount=0 시 `False` 반환.
   - `rebuild_index()` 호출 시 예외 없음.

**Exit criteria**:
- `pytest tests/unit/test_supabase_repository.py -q` PASS
- `ruff check src/trading_system/backtest/supabase_repository.py` 0 errors

---

### Step 9-3. SupabaseEquityWriter 구현

**목적**: `EquityWriterProtocol`을 Supabase PostgreSQL 기반으로 구현한다.

**파일**:
- `src/trading_system/app/supabase_equity_writer.py` (신규)
- `tests/unit/test_supabase_equity_writer.py` (신규)

**작업 항목**:
1. `supabase_equity_writer.py` 생성:
   - `SupabaseEquityWriter(database_url: str, session_id: str)` 클래스.
   - `session_id` property: 생성자에서 받은 값 반환.
   - `append(timestamp, equity, cash, positions_value)`: `INSERT INTO equity_snapshots (session_id, timestamp, equity, cash, positions_value) VALUES (...)`.
   - `read_recent(limit)`: `SELECT timestamp, equity, cash, positions_value FROM equity_snapshots WHERE session_id = %s ORDER BY timestamp DESC LIMIT %s`. 시간순 재정렬 후 `list[dict]` 반환.
   - 빈 결과 시 `[]` 반환.
2. `test_supabase_equity_writer.py` 작성 (mock 기반):
   - psycopg 커넥션/커서 mock.
   - `session_id` 속성이 생성자 전달값 반환.
   - `append()` 호출 시 INSERT SQL 실행됨.
   - `read_recent()` mock rows 반환 시 `list[dict]` 시간순 변환됨.
   - 빈 결과 시 `[]` 반환.

**Exit criteria**:
- `pytest tests/unit/test_supabase_equity_writer.py -q` PASS
- `ruff check src/trading_system/app/supabase_equity_writer.py` 0 errors

---

### Step 9-4. 저장소 전환 경로 통합

**목적**: `_RUN_REPOSITORY` 모듈 싱글턴과 `EquityWriter` 주입을 env-aware로 전환한다. 이 단계가 Codex Finding 1, 2의 핵심 해결책이다.

**파일**:
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/app/loop.py` (EquityWriter 생성 분기 확인)

**작업 항목**:
1. `backtest.py` 수정:
   - `_create_run_repository()` 팩토리 함수 추가:
     ```python
     def _create_run_repository() -> BacktestRunRepository:
         database_url = os.getenv("DATABASE_URL")
         if database_url:
             from trading_system.backtest.supabase_repository import SupabaseBacktestRunRepository
             return SupabaseBacktestRunRepository(database_url)
         return FileBacktestRunRepository(
             Path(os.getenv("TRADING_SYSTEM_RUNS_DIR", "data/runs"))
         )
     ```
   - 기존 `_RUN_REPOSITORY = FileBacktestRunRepository(...)` → `_RUN_REPOSITORY = _create_run_repository()` 교체.
   - `BacktestRunRepository` Protocol 임포트 추가 (타입 힌트용).
2. `analytics.py` 변경 불필요 확인: `from ...backtest import _RUN_REPOSITORY` 임포트가 factory 결과를 가져오므로 자동 교체.
3. `LiveTradingLoop` 생성 시 `equity_writer` 인자에 `DATABASE_URL` 기반 분기 추가:
   - `loop.py` 자체가 아닌, `LiveTradingLoop`를 생성하는 호출자 코드를 확인하여 `SupabaseEquityWriter` 또는 `FileEquityWriter`를 선택.
   - `services.py`의 `run_live_paper()` → `LiveTradingLoop(services=self)` 호출 시점에서, `equity_writer` 생성을 `DATABASE_URL` 기반으로 분기하는 헬퍼를 추가하거나, `LiveTradingLoop.__post_init__()`에서 처리.
4. 기존 테스트에서 `_RUN_REPOSITORY`를 monkeypatch하는 패턴이 있으면 동작 확인.
5. `DATABASE_URL` 없는 환경에서 `pytest --tb=short -q` 전체 PASS.

**Exit criteria**:
- `_RUN_REPOSITORY` factory가 `DATABASE_URL` 기반 분기 동작
- `analytics.py` 임포트가 자동 교체되어 동일 repository 사용
- `DATABASE_URL` 없는 환경에서 전체 테스트 PASS

---

### Step 9-5. FastAPI 백엔드 Railway 배포 설정

**목적**: Docker 컨테이너로 FastAPI 백엔드를 Railway에 배포할 수 있는 설정 파일을 추가한다.

**파일**:
- `src/trading_system/api/server.py`
- `Dockerfile` (신규)
- `railway.json` (신규)
- `.env.example` (기존 파일 확장)

**작업 항목**:
1. `server.py` 수정:
   - 모듈 하단에 `app = create_app()` 추가. 기존 `create_app()` 함수는 그대로 유지.
   - `GET /health` 엔드포인트 존재 확인. 없으면 `create_app()` 내에 추가:
     ```python
     @app.get("/health")
     def health():
         return {"status": "ok"}
     ```
2. `Dockerfile` 작성:
   ```dockerfile
   FROM python:3.12-slim
   WORKDIR /app
   COPY pyproject.toml uv.lock* ./
   COPY src/ ./src/
   COPY configs/ ./configs/
   RUN pip install --no-cache-dir -e .
   EXPOSE 8000
   CMD ["sh", "-c", "uvicorn trading_system.api.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
   ```
3. `railway.json` 작성:
   ```json
   {
     "$schema": "https://railway.app/railway.schema.json",
     "build": {
       "builder": "DOCKERFILE",
       "dockerfilePath": "Dockerfile"
     },
     "deploy": {
       "healthcheckPath": "/health",
       "healthcheckTimeout": 30,
       "restartPolicyType": "ON_FAILURE",
       "restartPolicyMaxRetries": 3
     }
   }
   ```
4. `.env.example` 확장 — 기존 파일에 Phase 9 항목 추가:
   ```
   # ── Database (Supabase) ───────────────────────
   # Supabase connection string. Leave empty for local file-based storage.
   DATABASE_URL=
   ```
5. `.gitignore`에 `.env` 포함 여부 확인. 없으면 추가.

**Exit criteria**:
- `docker build -t trading-system .` 성공
- `uvicorn trading_system.api.server:app` 실행 가능 (모듈 전역 `app` 사용)
- `GET /health` 200 응답
- `.env.example`에 `DATABASE_URL` 항목 추가됨

---

### Step 9-6. Next.js 프론트엔드 Vercel 배포 설정

**목적**: Vercel에 Next.js를 배포할 수 있도록 구성하고, 백엔드 URL 환경변수를 문서화한다.

**파일**:
- `frontend/.env.local.example` (기존 파일 보강)

**작업 항목**:
1. `frontend/.env.local.example` 보강:
   ```
   # FastAPI 백엔드 URL (Railway 배포 시 변경)
   # 값에 /api/v1 접미사를 포함해야 합니다.
   NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
   # 예: NEXT_PUBLIC_API_BASE_URL=https://my-backend.railway.app/api/v1
   ```
2. `apiStore.ts`에서 `NEXT_PUBLIC_API_BASE_URL` 사용 확인 — 변경 불필요.
3. `client.ts`에서 `useApiStore.getState().baseUrl` 사용 확인 — 변경 불필요.
4. SSE `EventSource` URL 구성이 `baseUrl` 기반인지 확인 — 변경 불필요.
5. `npx tsc --noEmit` PASS.
6. `npm run lint` PASS.
7. `npm run build` PASS.

**Exit criteria**:
- `frontend/.env.local.example` 보강 완료
- frontend build PASS

---

### Step 9-7. GitHub Actions CI 파이프라인

**목적**: `push`/`PR` 이벤트에 pytest + ruff + frontend build를 자동 검증하는 CI를 구성한다.

**파일**:
- `.github/workflows/ci.yml` (신규)

**작업 항목**:
1. `.github/workflows/` 디렉토리 생성 (없으면).
2. `ci.yml` 작성:
   ```yaml
   name: CI

   on:
     push:
     pull_request:

   jobs:
     python-ci:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v5
           with:
             python-version: "3.12"
             cache: "pip"
         - name: Install dependencies
           run: pip install -e ".[dev]"
         - name: Lint
           run: ruff check src/ tests/
         - name: Test
           run: pytest --tb=short -q

     frontend-ci:
       runs-on: ubuntu-latest
       defaults:
         run:
           working-directory: frontend
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-node@v4
           with:
             node-version: "20"
             cache: "npm"
             cache-dependency-path: frontend/package-lock.json
         - name: Install dependencies
           run: npm ci
         - name: Type check
           run: npx tsc --noEmit
         - name: Lint
           run: npm run lint
         - name: Build
           run: npm run build
           env:
             NEXT_PUBLIC_API_BASE_URL: http://localhost:8000/api/v1
   ```

**Exit criteria**:
- `ci.yml` 문법 오류 없음
- GitHub Actions에서 두 job 모두 PASS (push 후 확인)

---

### Step 9-8. 통합 검증 및 문서

**목적**: 전체 테스트를 통과하고 배포 가이드 문서를 갱신한다.

**파일**:
- `README.md`
- `frontend/.env.local.example`

**작업 항목**:
1. `pytest --tb=short -q` 전체 실행 PASS.
2. `ruff check src/ tests/` 0 errors.
3. `npx tsc --noEmit` PASS.
4. `npm run lint` PASS.
5. `npm run build` PASS.
6. `README.md`에 배포 가이드 섹션 추가:
   - **1단계: Supabase 프로젝트 생성**: 프로젝트 생성 → Connection String 복사 → `psql $DATABASE_URL -f scripts/migrations/001_create_backtest_runs.sql` → 002 실행.
   - **2단계: Railway 배포**: 리포지토리 연결 → 환경변수 설정 (`DATABASE_URL`, `TRADING_SYSTEM_ALLOWED_API_KEYS`, `TRADING_SYSTEM_CORS_ALLOW_ORIGINS`) → 배포 확인 `GET /health`.
   - **3단계: Vercel 배포**: 리포지토리 연결 → Root Directory: `frontend` → 환경변수 `NEXT_PUBLIC_API_BASE_URL=https://your-backend.railway.app/api/v1` → 배포 확인.
   - **CORS 설정**: Railway의 `TRADING_SYSTEM_CORS_ALLOW_ORIGINS`에 Vercel URL 추가 (트레일링 슬래시 없이).
   - README의 bilingual (한국어/영어) 규칙을 확인하여 준수.

**Exit criteria**:
- 전체 `pytest` PASS, `ruff` 0 errors, frontend 빌드 3종 PASS
- `README.md` 배포 섹션 갱신 완료

---

## Validation Matrix

### 단위 테스트

| 테스트 파일 | 검증 항목 |
|---|---|
| `tests/unit/test_supabase_repository.py` | CRUD mock, list 필터, delete rowcount, rebuild no-op |
| `tests/unit/test_supabase_equity_writer.py` | append INSERT, read_recent 변환, session_id 속성, 빈 결과 |

### 회귀 테스트

| 항목 | 기준 |
|---|---|
| `pytest --tb=short -q` | 전체 PASS (DATABASE_URL 없는 환경) |
| `ruff check src/ tests/` | 0 errors |
| `npx tsc --noEmit` | PASS |
| `npm run lint` | PASS |
| `npm run build` | PASS |

### 수동 검증 (배포 후)

| 항목 | 기준 |
|---|---|
| Railway 헬스체크 | `GET /health` → 200 `{"status": "ok"}` |
| Supabase DB 연결 | `GET /api/v1/backtests` → 200 (DB 연결 성공, 빈 목록) |
| 런 영속화 | POST 백테스트 → Railway 재배포 → `GET /api/v1/backtests` 목록에 이전 런 보존 |
| analytics 경로 | `GET /api/v1/analytics/backtests/{run_id}/trades` → Supabase에서 런 조회 (자동 교체 확인) |
| SSE 연결 | `curl -N https://backend.railway.app/api/v1/dashboard/stream?api_key=...` → heartbeat 수신 |
| CORS | Vercel 프론트에서 Railway API 요청 성공 (CORS 오류 없음) |
| 프론트 env | `NEXT_PUBLIC_API_BASE_URL` 설정 후 Vercel에서 API 호출 성공 |
| CI | GitHub Actions python-ci + frontend-ci 두 job PASS |

## PR Slices

| PR | 내용 |
|---|---|
| PR-1 | Step 9-0 + 9-1: 의존성 추가, EquityWriter Protocol 분리, SQL 마이그레이션 파일 |
| PR-2 | Step 9-2 + 9-3: SupabaseBacktestRunRepository + SupabaseEquityWriter (mock 테스트 포함) |
| PR-3 | Step 9-4: 저장소 전환 경로 통합 (`_RUN_REPOSITORY` factory, EquityWriter 분기) |
| PR-4 | Step 9-5: `server.py` app 전역, Dockerfile, railway.json, `.env.example` 확장 |
| PR-5 | Step 9-6 + 9-7: Vercel 설정, GitHub Actions CI |
| PR-6 | Step 9-8: 통합 검증, README 배포 가이드 |

## Risks and Fallbacks

| 리스크 | 완화 방안 |
|---|---|
| psycopg3 설치 실패 (slim 이미지 C 의존성) | `psycopg[binary]` 사용 (pre-compiled wheel 포함) |
| Supabase 연결 타임아웃 (Railway cold start) | `connect_timeout=10` 설정, 헬스체크 재시도 3회 |
| `_RUN_REPOSITORY` 모듈 임포트 시점 env 읽기 | 테스트에서 `_RUN_REPOSITORY` 자체를 monkeypatch (기존 패턴) |
| `BacktestRunDTO.result` JSONB 역직렬화 실패 | `FileBacktestRunRepository._deserialize_run()` 로직 재사용 |
| CI에서 psycopg import 오류 | Supabase 테스트에 `skipif DATABASE_URL` 마크 적용 |
| Railway `$PORT` 미주입 | CMD에 `${PORT:-8000}` 기본값 |
| CORS 오류 (Vercel → Railway) | `TRADING_SYSTEM_CORS_ALLOW_ORIGINS`에 Vercel URL 정확히 입력, `security.py` 변경 불필요 |
| analytics.py가 교체된 repository를 못 받음 | factory 방식이므로 임포트 시점에 자동 해결. 수동 검증 포함 |
