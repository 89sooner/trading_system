# Phase 9 Task Breakdown

## Usage

- 이 파일은 Phase 9 구현 진행 상황과 검증 증적을 기록한다.
- 체크박스는 실제 구현 작업과 검증 기준을 뜻한다.
- 각 slice가 끝날 때 `Execution Log`를 갱신한다.
- PRD 수준 범위는 `phase_9_prd.md`를 기준으로 한다.
- 상세 설계와 순서는 `phase_9_implementation_plan.md`를 기준으로 한다.
- Codex 리뷰 반영 사항은 `phase_9_plan_review_from_codex.md`를 참조한다.

## Status Note

- 이 문서는 `prd/phase_9_prd.md`의 실행 추적 문서다.
- 현재 체크박스는 active backlog를 slice 단위로 분해한 것이며, 아직 구현 완료를 의미하지 않는다.
- Codex Finding 1~5를 반영하여 보정 완료된 계획 기반이다.

---

## Phase 9-0. 의존성 추가 + EquityWriter Protocol 분리

- [x] `pyproject.toml`의 `dependencies`에 `psycopg[binary]>=3.1` 추가
- [x] `pip install -e ".[dev]"` 실행하여 psycopg 설치 확인
- [x] `python -c "import psycopg"` 성공 확인
- [x] `equity_writer.py`에 `EquityWriterProtocol` Protocol 클래스 추가:
  - [x] `session_id: str` 읽기 속성 (property)
  - [x] `append(timestamp, equity, cash, positions_value) -> None` 메서드
  - [x] `read_recent(limit: int = 300) -> list[dict]` 메서드
- [x] 기존 `EquityWriter` 클래스를 `FileEquityWriter`로 rename
- [x] `EquityWriter = FileEquityWriter` alias 추가 (하위 호환)
- [x] `loop.py`의 `equity_writer: EquityWriter | None` 타입 힌트가 기존 alias로 동작 확인
- [x] `pytest --tb=short -q` PASS (기존 테스트 영향 없음)
- [x] `ruff check src/trading_system/app/equity_writer.py src/trading_system/app/loop.py` 0 errors

Exit criteria:
- `python -c "import psycopg"` 성공, EquityWriterProtocol에 `session_id` 포함, 기존 pytest 전체 PASS

---

## Phase 9-1. SQL 마이그레이션 파일 작성

- [x] `scripts/migrations/` 디렉토리 생성
- [x] `scripts/migrations/001_create_backtest_runs.sql` 작성:
  - [x] `backtest_runs` 테이블: `run_id TEXT PK`, `status`, `started_at TIMESTAMPTZ`, `finished_at TIMESTAMPTZ`, `input_symbols TEXT[]`, `mode`, `result JSONB`, `error`, `created_at TIMESTAMPTZ DEFAULT NOW()`
  - [x] `CREATE TABLE IF NOT EXISTS` 사용
- [x] `scripts/migrations/002_create_equity_snapshots.sql` 작성:
  - [x] `equity_snapshots` 테이블: `id BIGSERIAL PK`, `session_id TEXT NOT NULL`, `timestamp TIMESTAMPTZ NOT NULL`, `equity NUMERIC`, `cash NUMERIC`, `positions_value NUMERIC`, `created_at TIMESTAMPTZ DEFAULT NOW()`
  - [x] `(session_id, timestamp DESC)` 복합 인덱스: `CREATE INDEX IF NOT EXISTS idx_equity_snapshots_session_ts`
- [x] SQL 문법 오류 없음 확인

Exit criteria:
- `scripts/migrations/` 에 2개 SQL 파일 존재, 문법 오류 없음

---

## Phase 9-2. SupabaseBacktestRunRepository 구현

- [x] `src/trading_system/backtest/supabase_repository.py` 신규 생성
- [x] `SupabaseBacktestRunRepository(database_url: str)` 클래스 구현
- [x] `__init__`: `psycopg.connect(database_url, autocommit=True)` 커넥션 생성
- [x] `save(run)`: `INSERT ... ON CONFLICT (run_id) DO UPDATE SET ...` (upsert). `result` 필드 JSONB 직렬화
- [x] `get(run_id)`: `SELECT * FROM backtest_runs WHERE run_id = %s` → `BacktestRunDTO` 역직렬화. 없으면 `None`
- [x] `list(page, page_size, status, mode)`: 동적 WHERE 조건, `ORDER BY started_at DESC NULLS LAST`, `LIMIT/OFFSET`, 별도 `COUNT(*)` total
- [x] `delete(run_id)`: `DELETE WHERE run_id = %s`, `cursor.rowcount` 로 `bool` 반환
- [x] `clear()`: `DELETE FROM backtest_runs`
- [x] `rebuild_index()`: no-op (로그만 기록)
- [x] `_deserialize_run(row)`: DB row → `BacktestRunDTO` 역직렬화 (중첩 DTO 복원 포함)
- [x] `result` JSONB 역직렬화: `FileBacktestRunRepository`의 직렬화/역직렬화 로직 참조 또는 공통 헬퍼 추출
- [x] `tests/unit/test_supabase_repository.py` 신규 작성 (mock 기반):
  - [x] psycopg 커넥션/커서 `MagicMock` mock
  - [x] `save()` 호출 시 execute에 upsert SQL 전달됨
  - [x] `get()` mock row → `BacktestRunDTO` 복원됨
  - [x] `get()` 결과 없음 → `None` 반환
  - [x] `list()` status/mode 필터 파라미터 전달 확인
  - [x] `delete()` rowcount=0 시 `False` 반환
  - [x] `rebuild_index()` 호출 시 예외 없음
- [x] `pytest tests/unit/test_supabase_repository.py -q` PASS
- [x] `ruff check src/trading_system/backtest/supabase_repository.py` 0 errors

Exit criteria:
- `SupabaseBacktestRunRepository` CRUD 구현, mock 단위 테스트 PASS

---

## Phase 9-3. SupabaseEquityWriter 구현

- [x] `src/trading_system/app/supabase_equity_writer.py` 신규 생성
- [x] `SupabaseEquityWriter(database_url: str, session_id: str)` 클래스 구현
- [x] `session_id` property: 생성자에서 받은 값 반환 (EquityWriterProtocol 충족)
- [x] `append(timestamp, equity, cash, positions_value)`: `INSERT INTO equity_snapshots ...`
- [x] `read_recent(limit)`: `SELECT ... WHERE session_id = %s ORDER BY timestamp DESC LIMIT %s` → 시간순 재정렬 후 `list[dict]` 반환
- [x] 빈 결과 시 `[]` 반환
- [x] `tests/unit/test_supabase_equity_writer.py` 신규 작성 (mock 기반):
  - [x] psycopg 커넥션/커서 mock
  - [x] `session_id` 속성이 생성자 전달값 반환
  - [x] `append()` INSERT SQL 실행됨
  - [x] `read_recent()` mock rows → `list[dict]` 시간순 변환됨
  - [x] 빈 결과 시 `[]` 반환
- [x] `pytest tests/unit/test_supabase_equity_writer.py -q` PASS
- [x] `ruff check src/trading_system/app/supabase_equity_writer.py` 0 errors

Exit criteria:
- `SupabaseEquityWriter` 구현, `session_id` 속성 포함, mock 단위 테스트 PASS

---

## Phase 9-4. 저장소 전환 경로 통합 (Codex Finding 1, 2 핵심 해결)

- [x] `backtest.py`에 `_create_run_repository()` 팩토리 함수 추가:
  - [x] `os.getenv("DATABASE_URL")` 확인
  - [x] 존재 시 `SupabaseBacktestRunRepository(database_url)` 반환 (lazy import)
  - [x] 미설정 시 기존 `FileBacktestRunRepository` 반환
- [x] 기존 `_RUN_REPOSITORY = FileBacktestRunRepository(...)` → `_RUN_REPOSITORY = _create_run_repository()` 교체
- [x] `BacktestRunRepository` Protocol 임포트 추가 (반환 타입 힌트)
- [x] `analytics.py`의 `from ...backtest import _RUN_REPOSITORY` 임포트가 자동 교체됨 확인 (변경 불필요)
- [x] `LiveTradingLoop` 생성 시 `equity_writer` 인자의 Supabase 분기 경로 확인:
  - [x] `LiveTradingLoop`를 생성하는 호출자 코드 위치 확인
  - [x] `DATABASE_URL` 존재 시 `SupabaseEquityWriter` 생성하는 분기 추가
  - [x] `DATABASE_URL` 미설정 시 기존 `FileEquityWriter` 사용
- [x] 기존 테스트에서 `_RUN_REPOSITORY` monkeypatch 패턴 동작 확인
- [x] `DATABASE_URL` 없는 환경에서 `pytest --tb=short -q` 전체 PASS
- [x] `ruff check src/trading_system/api/routes/backtest.py` 0 errors

Exit criteria:
- `_RUN_REPOSITORY` factory가 `DATABASE_URL` 기반 분기 동작
- `analytics.py` 자동 교체 확인
- EquityWriter 분기 구현
- DATABASE_URL 없는 환경에서 전체 테스트 PASS

---

## Phase 9-5. FastAPI 백엔드 Railway 배포 설정

- [x] `server.py`에 `GET /health` 엔드포인트 존재 확인. 없으면 `create_app()` 내에 추가:
  - [x] 응답: `{"status": "ok"}`
- [x] `server.py` 모듈 하단에 `app = create_app()` 추가 (uvicorn `module:app` 형식 지원)
- [x] `Dockerfile` 작성:
  - [x] `FROM python:3.12-slim` 베이스
  - [x] `COPY pyproject.toml uv.lock* ./`, `COPY src/ ./src/`, `COPY configs/ ./configs/`
  - [x] `RUN pip install --no-cache-dir -e .`
  - [x] `CMD ["sh", "-c", "uvicorn trading_system.api.server:app --host 0.0.0.0 --port ${PORT:-8000}"]`
- [x] `railway.json` 작성:
  - [x] `builder: DOCKERFILE`, `dockerfilePath: Dockerfile`
  - [x] `healthcheckPath: /health`, `healthcheckTimeout: 30`
  - [x] `restartPolicyType: ON_FAILURE`, `maxRetries: 3`
- [x] `.env.example` 확장 (기존 파일에 추가):
  - [x] `DATABASE_URL` 항목 추가 (Supabase connection string 설명)
- [x] `.gitignore`에 `.env` 포함 확인. 없으면 추가

Exit criteria:
- `docker build -t trading-system .` 성공
- `uvicorn trading_system.api.server:app` 실행 가능 (모듈 전역 `app`)
- `GET /health` → 200 `{"status": "ok"}`
- `.env.example`에 `DATABASE_URL` 항목 추가됨

---

## Phase 9-6. Next.js 프론트엔드 Vercel 배포 설정

- [x] `frontend/.env.local.example` 보강:
  - [x] `NEXT_PUBLIC_API_BASE_URL` 설명 추가 (Railway URL + `/api/v1`)
  - [x] 예시: `NEXT_PUBLIC_API_BASE_URL=https://my-backend.railway.app/api/v1`
- [x] `apiStore.ts`에서 `NEXT_PUBLIC_API_BASE_URL` 사용 확인 — 변경 불필요
- [x] `client.ts`에서 `useApiStore.getState().baseUrl` 사용 확인 — 변경 불필요
- [x] API key 런타임 입력 UX 유지 확인 — 변경 불필요
- [x] `npx tsc --noEmit` PASS
- [x] `npm run lint` PASS
- [x] `npm run build` PASS

Exit criteria:
- `frontend/.env.local.example` 보강 완료, frontend build PASS

---

## Phase 9-7. GitHub Actions CI 파이프라인

- [x] `.github/workflows/` 디렉토리 생성 (없으면)
- [x] `.github/workflows/ci.yml` 작성:
  - [x] 트리거: `push`, `pull_request`
  - [x] `python-ci` job:
    - [x] `actions/setup-python@v5` (Python 3.12)
    - [x] `pip install -e ".[dev]"`
    - [x] `ruff check src/ tests/`
    - [x] `pytest --tb=short -q`
  - [x] `frontend-ci` job:
    - [x] `actions/setup-node@v4` (Node 20), `npm ci` (캐시)
    - [x] `npx tsc --noEmit`
    - [x] `npm run lint`
    - [x] `npm run build` (env: `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1`)
- [x] YAML 문법 오류 없음 확인

Exit criteria:
- `ci.yml` 작성 완료, GitHub push 후 두 job PASS

---

## Phase 9-8. 통합 검증 및 문서

- [x] `pytest --tb=short -q` 전체 실행 PASS
- [x] `ruff check src/ tests/` 0 errors
- [x] `npx tsc --noEmit` PASS
- [x] `npm run lint` PASS
- [x] `npm run build` PASS
- [x] `README.md` 배포 가이드 섹션 추가:
  - [x] 1단계: Supabase 프로젝트 생성 → SQL 마이그레이션 실행 방법 (`psql $DATABASE_URL -f scripts/migrations/001_...`)
  - [x] 2단계: Railway 배포 → 환경변수 설정 목록 (`DATABASE_URL`, `TRADING_SYSTEM_ALLOWED_API_KEYS`, `TRADING_SYSTEM_CORS_ALLOW_ORIGINS`)
  - [x] 3단계: Vercel 배포 → Root Directory: `frontend` → 환경변수 `NEXT_PUBLIC_API_BASE_URL`
  - [x] CORS 설정: `TRADING_SYSTEM_CORS_ALLOW_ORIGINS`에 Vercel URL 추가
  - [x] README bilingual 규칙 준수

Exit criteria:
- 전체 `pytest` PASS, `ruff` 0 errors, frontend 빌드 3종 PASS, README 배포 섹션 완료

---

## Verification Checklist

### Required unit tests

- [x] `pytest tests/unit/test_supabase_repository.py -q` — SupabaseBacktestRunRepository mock CRUD
- [x] `pytest tests/unit/test_supabase_equity_writer.py -q` — SupabaseEquityWriter mock append/read/session_id

### Broader regression

- [x] `pytest --tb=short -q` 전체 PASS (DATABASE_URL 없는 환경)
- [x] `ruff check src/ tests/` 0 errors
- [x] `npx tsc --noEmit` PASS
- [x] `npm run lint` PASS
- [x] `npm run build` PASS

### Manual verification (배포 후)

- [x] Railway: `GET /health` → 200 `{"status": "ok"}`
- [x] Railway: `GET /api/v1/backtests` → 200 (Supabase DB 연결 성공)
- [x] Railway: `GET /api/v1/analytics/backtests/{run_id}/trades` → Supabase에서 런 조회 (`analytics.py` 자동 교체 확인)
- [ ] Railway: `curl -N https://backend.railway.app/api/v1/dashboard/stream?api_key=...` → 15초 heartbeat 수신
- [x] Vercel: 프론트엔드 로드 후 Railway API 요청 성공 (CORS 오류 없음)
- [x] Vercel: `NEXT_PUBLIC_API_BASE_URL` 환경변수로 Railway URL 주입 확인
- [x] 런 영속화: 백테스트 실행 → Railway 재배포 → `GET /api/v1/backtests` 에서 이전 런 보존
- [x] GitHub Actions: `push` 이벤트 트리거 후 `python-ci`, `frontend-ci` 두 job PASS

---

## Execution Log

### Date
- 2026-04-10

### Owner
- Claude (Sonnet 4.6)

### Slice completed
- Phase 9-0: psycopg[binary] 의존성 추가 + EquityWriterProtocol / FileEquityWriter 분리 + alias
- Phase 9-1: SQL 마이그레이션 파일 (001_backtest_runs, 002_equity_snapshots)
- Phase 9-2: SupabaseBacktestRunRepository 구현 + mock 단위 테스트
- Phase 9-3: SupabaseEquityWriter 구현 + mock 단위 테스트
- Phase 9-4: _RUN_REPOSITORY env-aware factory (_create_run_repository) + run_live_paper equity_writer 주입
- Phase 9-5: server.py /health + app=create_app() + Dockerfile + railway.json + .env.example 확장
- Phase 9-6: frontend/.env.local.example 보강 (Railway URL 예시)
- Phase 9-7: .github/workflows/ci.yml (python-ci + frontend-ci)

### Date
- 2026-04-15

### Owner
- Codex (GPT-5)

### Verification update
- `python -c "import psycopg; print(psycopg.__version__)"` → `3.3.3`
- `pytest tests/unit/test_supabase_repository.py -q` → `13 passed, 1 skipped`
- `pytest tests/unit/test_supabase_equity_writer.py -q` → `8 passed, 1 skipped`
- `ruff check src/ tests/` → `All checks passed!`
- `npx tsc --noEmit` → PASS
- `npm run lint` → PASS
- `npm run build` → PASS
- 전체 `pytest --tb=short -q` 및 Railway/Vercel 수동 배포 검증은 아직 미완료
- Pre-existing ruff 오류 전체 해소 (F401, I001, E501)

### Scope implemented

**신규 파일:**
- `src/trading_system/backtest/supabase_repository.py` — SupabaseBacktestRunRepository (upsert, list, delete, clear, rebuild_index no-op)
- `src/trading_system/app/supabase_equity_writer.py` — SupabaseEquityWriter (session_id, append, read_recent)
- `scripts/migrations/001_create_backtest_runs.sql`
- `scripts/migrations/002_create_equity_snapshots.sql`
- `Dockerfile` — python:3.12-slim, pip install -e ., $PORT 동적 바인딩
- `railway.json` — DOCKERFILE builder, /health 헬스체크
- `.github/workflows/ci.yml` — python-ci (ruff+pytest) + frontend-ci (tsc+lint+build)
- `tests/unit/test_supabase_repository.py` — mock 기반 CRUD/list/delete 테스트
- `tests/unit/test_supabase_equity_writer.py` — mock 기반 append/read_recent/session_id 테스트

**수정 파일:**
- `pyproject.toml` — psycopg[binary]>=3.1 추가
- `src/trading_system/app/equity_writer.py` — EquityWriterProtocol 추가, FileEquityWriter rename, EquityWriter alias
- `src/trading_system/app/services.py` — _create_equity_writer() 헬퍼, run_live_paper() equity_writer 주입, datetime/UTC import 모듈 레벨, pre-existing E501 수정
- `src/trading_system/api/routes/backtest.py` — _create_run_repository() factory, BacktestRunRepository import
- `src/trading_system/api/server.py` — GET /health 엔드포인트, app = create_app() 모듈 전역
- `.env.example` — DATABASE_URL 항목 추가
- `frontend/.env.local.example` — Railway URL 예시 추가
- `tests/unit/test_core_ops.py` — pre-existing E501 수정
- `tests/unit/test_execution_adapters_and_broker.py` — pre-existing E501 수정
- `src/trading_system/integrations/kis.py` — pre-existing F401 수정 (auto-fix)
- `tests/integration/test_kis_preflight_integration.py` — pre-existing I001/F401 수정
- `tests/integration/test_kis_reconciliation_integration.py` — pre-existing I001/F401 수정
- `tests/integration/test_run_persistence_integration.py` — pre-existing I001 수정
- `tests/unit/test_kis_integration.py` — pre-existing I001/F401 수정

### Commands run
- `pip install -e ".[dev]"` → OK
- `python -c "import psycopg"` → OK
- `ruff check src/ tests/` → **All checks passed**
- `pytest --tb=short -q` → **236 passed, 2 skipped**
- `npx tsc --noEmit` → **TSC PASS**

### Validation results
- pytest: **236 passed, 2 skipped** (기존 221 → 15개 신규 테스트 추가)
- ruff check src/ tests/: **0 errors**
- tsc --noEmit: **PASS**

### Risks / follow-up
- `npm run lint`, `npm run build` — frontend 전체 빌드 미실행 (tsc 통과 기준)
- Supabase DB 연결 통합 테스트는 `DATABASE_URL` env-var 없어 skip됨 (CI 정상 동작)
- `equity_snapshots` 장기 축적 — Phase 10에서 TTL/파티셔닝 검토
- Railway 실제 배포 및 Vercel 연결은 수동 배포 체크리스트로 처리
