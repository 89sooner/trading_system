# Phase 9 PRD

관련 문서:
- 이전 phase 범위/결과: `prd/phase_8_prd.md`
- 이전 phase 실행 검증: `prd/phase_8_task.md`
- 상세 구현 계획: `prd/phase_9_implementation_plan.md`
- 실행 추적: `prd/phase_9_task.md`
- Codex 리뷰: `prd/phase_9_plan_review_from_codex.md`

## 문서 목적

이 문서는 Phase 8까지 구축된 트레이딩 시스템을 **Vercel(프론트엔드), Railway(FastAPI 백엔드), Supabase(PostgreSQL 데이터베이스)** 에 배포하여 실제 운영 환경에서 사용할 수 있도록 인프라를 구축하는 `Phase 9` 범위를 정의한다.

현재 시스템은 로컬 실행에만 동작하며, 파일 기반 영속화(`data/runs/`, `data/equity/`)는 서버 환경에서 컨테이너 재배포 시 데이터가 유실되는 구조적 한계가 있다. Phase 9는 이 한계를 해소하고, 외부에서 접근 가능한 운영 환경을 구성하여 시스템을 실제 서비스로 전환하는 것을 목표로 한다.

## Goal

1. Next.js 프론트엔드를 Vercel에 배포하여 외부 URL로 접근 가능하게 한다.
2. FastAPI 백엔드를 Railway에 배포하여 SSE 장기 연결을 포함한 모든 API 엔드포인트를 외부에서 사용 가능하게 한다.
3. 파일 기반 영속화(`FileBacktestRunRepository`, `EquityWriter`)를 Supabase PostgreSQL 기반으로 교체하여 컨테이너 재배포 후에도 데이터를 보존한다.
4. 환경변수 기반 비밀 관리 체계를 구축하여 개발/운영 환경을 분리한다.
5. GitHub Actions 기반 기본 CI 파이프라인을 구축하여 PR마다 테스트·린트·빌드를 자동 검증한다.

구현은 반드시 다음 원칙을 지켜야 한다.

- 기존 API contract(`/api/v1/*`)의 하위 호환성을 유지한다. 응답 형태를 변경하지 않는다.
- `BacktestRunRepository` Protocol 인터페이스를 유지한다. 구현체만 교체한다.
- `EquityWriter`를 Protocol로 분리하되, 기존 `session_id` 속성과 `append`, `read_recent` 메서드를 모두 포함한다.
- 로컬 개발 환경은 `DATABASE_URL` 미설정 시 기존 파일 기반 영속화로 계속 동작해야 한다.
- SSE 스트리밍은 Railway에서 그대로 동작한다 (Vercel 서버리스 미사용).
- 기존 보안 미들웨어(`security.py`)의 CORS 처리 방식을 유지한다. `CORSMiddleware`를 별도 추가하지 않는다.

## Current Baseline

- `_RUN_REPOSITORY`: `api/routes/backtest.py` 모듈 전역 `FileBacktestRunRepository` 싱글턴. `build_services()`를 경유하지 않는다. `analytics.py`도 이 싱글턴을 직접 임포트하여 사용한다.
- `EquityWriter`: 구체 클래스. `append`, `read_recent` 메서드 + `session_id` 프로퍼티 보유. `LiveTradingLoop`의 `equity_writer: EquityWriter | None` 필드로 주입. `AppServices`에는 `equity_writer` 필드가 없다.
- `BacktestRunRepository` Protocol: `save`, `get`, `list`, `delete`, `clear`, `rebuild_index` 6개 메서드.
- CORS 처리: `security.py`의 `build_security_middleware()`가 자체 CORS 헤더를 직접 관리. FastAPI `CORSMiddleware`를 사용하지 않는다.
- CORS env-var: `TRADING_SYSTEM_CORS_ALLOW_ORIGINS` (현재 이름). `configs/base.yaml`의 기본값은 `*`.
- 프론트엔드 API URL: `NEXT_PUBLIC_API_BASE_URL` env-var로 주입 (기본값 `http://127.0.0.1:8000/api/v1`, `/api/v1` 접미사 포함). `apiStore.ts` Zustand 스토어에서 관리.
- 프론트엔드 API key: 환경변수가 아닌 Zustand 스토어에 운영자가 런타임 입력. `apiStore.ts`의 `apiKey` 상태.
- `server.py`: `create_app()` 팩토리 함수만 존재. 모듈 전역 `app` 인스턴스 없음. uvicorn `--factory` 모드 또는 모듈 레벨 `app = create_app()` 추가 필요.
- `.env.example`: 이미 존재하는 파일. Phase 9에서 신규 생성이 아니라 확장/보강 대상.
- `GET /api/v1/dashboard/stream`: SSE 장기 연결 엔드포인트 (Railway에서 지원, Vercel 서버리스 미지원).
- `build_services()`: `AppSettings` 기반 서비스 조립. `AppServices`에 `webhook_notifier` 포함.
- Phase 8 완료: 파일 기반 영속화, SSE 스트리밍, Webhook 알림, 221개 pytest PASS.

## Non-Goals

- Supabase Auth 도입 (기존 API key 기반 인증 유지)
- Supabase Realtime 도입 (기존 FastAPI SSE 엔드포인트 유지)
- Supabase Storage 사용 (바이너리/파일 업로드 없음)
- WebSocket 도입
- FastAPI `CORSMiddleware` 추가 (기존 security middleware CORS 유지)
- 멀티 리전 배포
- CDN 최적화
- 모니터링/APM 도구 연동 (Datadog, Sentry 등)
- Kubernetes/ECS 기반 배포
- Blue-Green 또는 Canary 배포 전략
- 백테스트 결과 비교 뷰
- Railway 자동 스케일링 설정
- Supabase Row Level Security (RLS) 설정
- 프론트엔드 API key 환경변수 주입 (기존 런타임 입력 방식 유지)

## Hard Decisions

### D-1. FastAPI 백엔드는 Railway에 배포한다 (Vercel 서버리스 대신)

- Vercel 서버리스 함수는 실행 타임아웃(기본 10초, 최대 60초)이 있어 SSE 장기 연결을 지원하지 않는다.
- Railway는 컨테이너 기반으로 장기 프로세스를 지원하며, Vercel + Supabase 스택과 조합이 일반적이다.
- `Dockerfile`을 추가하여 Railway에 배포한다.
- `server.py`에 모듈 전역 `app = create_app()`을 추가하여 uvicorn의 표준 `module:app` 형식을 지원한다.
- Railway의 `$PORT` 환경변수를 uvicorn 포트로 주입한다.

### D-2. Supabase PostgreSQL로 파일 기반 영속화를 교체한다

- 컨테이너 재배포(Railway deploy) 시 로컬 파일(`data/runs/`, `data/equity/`)은 초기화된다.
- Supabase PostgreSQL을 운영 환경 영속화 백엔드로 사용한다.
- Python 클라이언트: `psycopg[binary]>=3.1` (동기 드라이버, 기존 Repository 인터페이스와 호환).
- `SupabaseBacktestRunRepository`: 기존 `BacktestRunRepository` Protocol 구현체로 추가.
- `SupabaseEquityWriter`: 기존 `EquityWriter` Protocol 구현체로 추가.
- 로컬 환경: `DATABASE_URL` env-var 미설정 시 `FileBacktestRunRepository` + `FileEquityWriter` 사용 (기존 동작 유지).
- 운영 환경: `DATABASE_URL` 설정 시 Supabase 구현체 자동 선택.

### D-3. `_RUN_REPOSITORY` 모듈 싱글턴을 env-aware factory로 교체한다

- **Codex Finding 1 반영**. 현재 `_RUN_REPOSITORY`는 `backtest.py` 모듈 전역에서 `FileBacktestRunRepository`로 하드코딩되며, `analytics.py`도 이를 직접 임포트한다. `build_services()` 경로를 경유하지 않는다.
- `backtest.py`의 `_RUN_REPOSITORY` 초기화를 `_create_run_repository()` 팩토리 함수로 교체한다:
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
- `analytics.py`는 기존처럼 `from ...backtest import _RUN_REPOSITORY`로 임포트하므로 자동으로 교체된다.
- 이 방식은 기존 모듈 구조와 임포트 패턴을 최소한으로 변경하면서 env-aware 전환을 달성한다.

### D-4. EquityWriter Protocol에 `session_id` 속성을 포함한다

- **Codex Finding 2 반영**. 현재 `GET /api/v1/dashboard/equity` 엔드포인트가 `equity_writer.session_id`를 읽어 응답에 포함한다.
- `EquityWriterProtocol`에 `session_id: str` 읽기 속성을 명시한다.
- `EquityWriter`(→ `FileEquityWriter`) 주입 경로는 `LiveTradingLoop.__init__`의 `equity_writer` 필드이며, `AppServices`에는 추가하지 않는다.
- `session_id` 생성 정책: 기존 `LiveTradingLoop` 생성 시 호출자가 `session_id`를 전달하는 구조를 유지한다. Phase 9에서는 이 정책을 변경하지 않는다.

### D-5. 기존 security middleware의 CORS 처리를 유지한다

- **Codex Finding 3 반영**. 현재 CORS는 `security.py`의 `build_security_middleware()`가 자체적으로 처리하며, `_cors_headers()` 함수로 `Access-Control-Allow-Origin` 등을 직접 관리한다. FastAPI `CORSMiddleware`를 사용하지 않는다.
- env-var 이름은 기존 `TRADING_SYSTEM_CORS_ALLOW_ORIGINS`를 유지한다 (문서에서 잘못 적었던 `TRADING_SYSTEM_CORS_ORIGINS` 수정).
- `configs/base.yaml`의 기본값은 `*`이다 (문서에서 잘못 적었던 "localhost만 허용" 수정).
- Vercel 배포 URL은 `TRADING_SYSTEM_CORS_ALLOW_ORIGINS` env-var에 추가하면 기존 메커니즘으로 자동 처리된다.
- `security.py` 코드 변경이 필요 없다. 환경변수 설정만으로 CORS가 해결된다.

### D-6. 프론트엔드 env 체계는 기존 `NEXT_PUBLIC_API_BASE_URL`을 유지한다

- **Codex Finding 4 반영**. 현재 프론트엔드는 `NEXT_PUBLIC_API_BASE_URL` env-var를 사용하며 값에 `/api/v1` 접미사를 포함한다 (`http://127.0.0.1:8000/api/v1`).
- API key는 `NEXT_PUBLIC_API_KEY` env-var가 아니라, `apiStore.ts` Zustand 스토어에 운영자가 런타임에 입력하는 구조다.
- Phase 9에서는 `NEXT_PUBLIC_API_BASE_URL`을 Vercel 환경변수로 Railway 백엔드 URL + `/api/v1`을 설정하는 수준으로 충분하다 (예: `https://my-backend.railway.app/api/v1`).
- API key 런타임 입력 UX를 유지한다. `NEXT_PUBLIC_API_KEY` 도입은 하지 않는다.

### D-7. DB 스키마는 SQL 마이그레이션 파일로 관리한다 (Alembic 미사용)

- 현재 규모에서 Alembic 설정 오버헤드를 피하기 위해 `scripts/migrations/` 디렉토리에 번호 붙은 SQL 파일로 관리한다.
- 마이그레이션은 Supabase 대시보드 SQL Editor 또는 `psql` CLI로 수동 실행한다.

### D-8. `server.py`에 모듈 전역 `app`을 추가한다

- **Codex Finding 5 반영**. 현재 `server.py`에는 `create_app()` 팩토리만 있고 모듈 전역 `app`이 없다.
- `app = create_app()` 를 모듈 하단에 추가하여 uvicorn의 `trading_system.api.server:app` 형식을 지원한다.
- `Dockerfile`의 `CMD`는 이 모듈 전역 `app`을 참조한다.

### D-9. `.env.example`은 기존 파일을 확장한다

- **Codex Finding 5 반영**. `.env.example`은 이미 존재하는 파일이다. 신규 생성이 아니라 `DATABASE_URL` 등 Phase 9 신규 항목을 추가하는 방식으로 확장한다.

### D-10. GitHub Actions CI는 test·lint·build 3단계로 구성한다

- `push`/`PR` 이벤트에 트리거.
- Job 1: `pytest` 전체 실행 (Python 환경).
- Job 2: `ruff check` lint (Python 환경, 동일 Job에 통합 가능).
- Job 3: `npm run build` + `npx tsc --noEmit` + `npm run lint` (Node.js 환경).
- CD(자동 배포)는 이번 Phase 범위에서 제외한다. Railway/Vercel의 Git 연동 자동 배포로 대체한다.

## Product Requirements

### PR-1. Supabase 데이터베이스 스키마

- `backtest_runs` 테이블: `run_id TEXT PK`, `status TEXT`, `started_at TIMESTAMPTZ`, `finished_at TIMESTAMPTZ`, `input_symbols TEXT[]`, `mode TEXT`, `result JSONB`, `error TEXT`, `created_at TIMESTAMPTZ DEFAULT NOW()`.
- `equity_snapshots` 테이블: `id BIGSERIAL PK`, `session_id TEXT NOT NULL`, `timestamp TIMESTAMPTZ NOT NULL`, `equity NUMERIC`, `cash NUMERIC`, `positions_value NUMERIC`, `created_at TIMESTAMPTZ DEFAULT NOW()`.
- `equity_snapshots(session_id, timestamp DESC)` 복합 인덱스.
- 마이그레이션 SQL 파일은 `scripts/migrations/` 에 저장한다.

### PR-2. SupabaseBacktestRunRepository

- `BacktestRunRepository` Protocol 구현체.
- `save(run)`: `INSERT ... ON CONFLICT DO UPDATE` (upsert) 방식으로 저장. `result` 필드는 JSONB 직렬화.
- `get(run_id)`: `SELECT` → `BacktestRunDTO` 역직렬화. 없으면 `None`.
- `list(page, page_size, status, mode)`: 필터, `ORDER BY started_at DESC`, `LIMIT/OFFSET` 페이지네이션.
- `delete(run_id)`: `DELETE WHERE run_id=?`. 없으면 `False`.
- `clear()`: `DELETE FROM backtest_runs`.
- `rebuild_index()`: no-op (DB에서 불필요, 인터페이스 호환성 유지).
- 연결: `DATABASE_URL` env-var에서 읽은 psycopg3 커넥션.

### PR-3. SupabaseEquityWriter

- `EquityWriterProtocol` 구현체. `session_id` 속성 + `append`, `read_recent` 메서드.
- `append(timestamp, equity, cash, positions_value)`: `INSERT INTO equity_snapshots ...`.
- `read_recent(limit)`: `SELECT ... WHERE session_id=? ORDER BY timestamp DESC LIMIT ?` → 시간순 재정렬 후 반환.
- `session_id`: 생성자에서 전달받은 값을 그대로 반환.

### PR-4. `_RUN_REPOSITORY` env-aware factory 전환

- `backtest.py`의 `_RUN_REPOSITORY` 초기화를 `_create_run_repository()` 팩토리로 교체.
- `DATABASE_URL` 존재 시 `SupabaseBacktestRunRepository`, 미설정 시 `FileBacktestRunRepository`.
- `analytics.py`의 `from ...backtest import _RUN_REPOSITORY` 임포트는 변경 없이 자동 교체.
- 기존 테스트는 `monkeypatch`로 `_RUN_REPOSITORY`를 InMemory로 대체하여 격리 유지.

### PR-5. EquityWriter Protocol 분리 + LiveTradingLoop 주입 경로 유지

- `equity_writer.py`에 `EquityWriterProtocol` 추가: `session_id: str` 속성 + `append`, `read_recent` 메서드.
- 기존 `EquityWriter`를 `FileEquityWriter`로 rename. `EquityWriter = FileEquityWriter` alias 유지.
- `LiveTradingLoop`의 `equity_writer` 타입 힌트를 `EquityWriterProtocol | None`으로 변경.
- `LiveTradingLoop` 생성 시 `equity_writer` 주입은 기존 호출자 경로를 유지. `AppServices`에 `equity_writer` 필드를 추가하지 않는다.
- `dashboard.py`의 `equity_writer.session_id` 접근은 기존 동작 유지.

### PR-6. FastAPI 백엔드 Railway 배포 설정

- `Dockerfile` 추가: Python 3.12-slim 기반, `pip install -e .`, uvicorn 실행.
- `server.py`에 `app = create_app()` 모듈 전역 인스턴스 추가.
- `railway.json` 추가: 빌드 명령, 시작 명령, 헬스체크 경로 정의.
- 헬스체크 엔드포인트 `GET /health` 확인 또는 추가.
- `$PORT` 환경변수로 uvicorn 포트 동적 바인딩.

### PR-7. Next.js 프론트엔드 Vercel 배포 설정

- Vercel 대시보드에서 `frontend/` 루트 디렉토리 설정.
- `NEXT_PUBLIC_API_BASE_URL` 환경변수를 Railway 배포 URL + `/api/v1`로 설정 (예: `https://my-backend.railway.app/api/v1`).
- 기존 `apiStore.ts`의 런타임 override UX를 유지한다. env-var는 기본값 역할.
- API key는 런타임 입력 방식 유지. `NEXT_PUBLIC_API_KEY` 도입하지 않는다.

### PR-8. 환경변수 문서화

- `.env.example` 확장: `DATABASE_URL` 등 Phase 9 신규 항목 추가. 기존 항목은 유지.
- `frontend/.env.local.example` 확인: Vercel 배포 시 Railway URL 예시 추가.
- `README.md` 배포 섹션 갱신: Supabase 프로젝트 생성 → 마이그레이션 실행 → Railway 배포 → Vercel 배포 순서.

### PR-9. GitHub Actions CI 파이프라인

- `.github/workflows/ci.yml` 추가.
- 트리거: `push`, `pull_request`.
- Job `python-ci`: `pip install -e ".[dev]"` → `ruff check src/ tests/` → `pytest --tb=short -q`.
- Job `frontend-ci`: `npm ci` → `npx tsc --noEmit` → `npm run lint` → `npm run build`.

## Scope By Epic

### Epic A. Supabase 데이터베이스 스키마 및 Repository 구현

목표:
- 파일 기반 영속화를 Supabase PostgreSQL로 교체하고, 로컬 환경에서는 기존 파일 기반이 계속 동작한다.

포함:
- SQL 마이그레이션 파일 (backtest_runs, equity_snapshots)
- `psycopg[binary]>=3.1` 의존성 추가
- `SupabaseBacktestRunRepository` 구현
- `SupabaseEquityWriter` 구현
- `EquityWriterProtocol` 분리 + `FileEquityWriter` rename
- 단위 테스트 (psycopg mock)

제외:
- Supabase Auth, Storage, Realtime
- Alembic 자동 마이그레이션
- 기존 FileBacktestRunRepository/FileEquityWriter 제거

### Epic B. 저장소 전환 경로 통합

목표:
- `_RUN_REPOSITORY` 모듈 싱글턴과 `EquityWriter` 주입 경로를 env-aware로 전환하여, `DATABASE_URL` 설정 시 Supabase 구현체가 실제 실행 경로에 투입된다.

포함:
- `backtest.py`의 `_RUN_REPOSITORY`를 `_create_run_repository()` factory로 교체
- `analytics.py`의 `_RUN_REPOSITORY` 임포트 자동 교체 확인
- `LiveTradingLoop` 생성 시 `EquityWriter` 구현체 분기 (파일/Supabase)
- 기존 테스트의 `_RUN_REPOSITORY` monkeypatch 격리 확인

제외:
- `AppServices`에 `run_repository` 또는 `equity_writer` 필드 추가
- `_RUN_REPOSITORY`를 `app.state` 의존성 주입으로 전환 (현재 모듈 패턴 유지)

### Epic C. FastAPI 백엔드 Railway 배포 설정

목표:
- Docker 컨테이너로 FastAPI 백엔드를 Railway에 배포할 수 있는 설정 파일을 추가한다.

포함:
- `server.py`에 `app = create_app()` 모듈 전역 인스턴스 추가
- `Dockerfile`
- `railway.json`
- `GET /health` 엔드포인트 확인/추가
- `.env.example` 확장 (`DATABASE_URL` 등 추가)

제외:
- Railway 자동 스케일링
- 커스텀 도메인 연결 (Railway 대시보드에서 수동 설정)
- `CORSMiddleware` 추가 (기존 security middleware CORS 유지)

### Epic D. Next.js 프론트엔드 Vercel 배포 설정

목표:
- Next.js 프론트엔드를 Vercel에 배포할 수 있도록 구성하고, 백엔드 URL을 환경변수로 주입한다.

포함:
- `NEXT_PUBLIC_API_BASE_URL` 환경변수를 Vercel 대시보드에서 설정하는 가이드
- `frontend/.env.local.example` 보강 (Railway URL 예시)

제외:
- `NEXT_PUBLIC_API_KEY` 환경변수 도입 (런타임 입력 유지)
- `NEXT_PUBLIC_API_URL` 새 env-var 도입
- Vercel Edge Functions, Vercel Analytics
- 커스텀 도메인 연결 (Vercel 대시보드에서 수동 설정)

### Epic E. GitHub Actions CI

목표:
- PR 시 자동으로 Python 테스트·린트와 프론트엔드 빌드를 검증한다.

포함:
- `.github/workflows/ci.yml`
- Python CI job (pytest + ruff)
- Frontend CI job (tsc + lint + build)

제외:
- CD(자동 배포) — Railway/Vercel Git 연동으로 대체
- E2E 테스트 CI 실행 (로컬 서버 의존성으로 제외)
- 커버리지 리포트

### Epic F. 통합 검증 및 문서

목표:
- 로컬 환경에서 전체 회귀 테스트를 통과하고, 배포 가이드를 문서화한다.

포함:
- `pytest` 전체 실행
- `ruff check` 0 errors
- `npm run build`, `npx tsc --noEmit`, `npm run lint` PASS
- `README.md` 배포 섹션 갱신 (한국어/영어 bilingual 규칙 반영)

## Impacted Files

### 신규 생성 (백엔드)
- `Dockerfile`
- `railway.json`
- `scripts/migrations/001_create_backtest_runs.sql`
- `scripts/migrations/002_create_equity_snapshots.sql`
- `src/trading_system/backtest/supabase_repository.py`
- `src/trading_system/app/supabase_equity_writer.py`
- `tests/unit/test_supabase_repository.py`
- `tests/unit/test_supabase_equity_writer.py`

### 신규 생성 (CI)
- `.github/workflows/ci.yml`

### 수정 대상 (백엔드)
- `pyproject.toml` — `psycopg[binary]>=3.1` 의존성 추가
- `src/trading_system/api/server.py` — `app = create_app()` 모듈 전역 인스턴스 추가
- `src/trading_system/api/routes/backtest.py` — `_RUN_REPOSITORY` 초기화를 `_create_run_repository()` factory로 교체
- `src/trading_system/app/equity_writer.py` — `EquityWriterProtocol` 추가, `EquityWriter` → `FileEquityWriter` rename, alias 유지
- `src/trading_system/app/loop.py` — `equity_writer` 타입 힌트를 `EquityWriterProtocol | None`으로 변경
- `.env.example` — `DATABASE_URL` 등 Phase 9 신규 항목 추가

### 수정 대상 (프론트엔드)
- `frontend/.env.local.example` — Railway URL 예시 추가

### 문서
- `README.md` — 배포 가이드 섹션 추가 (Supabase → Railway → Vercel 순서)

### 변경 없음 (명시적 확인)
- `src/trading_system/api/security.py` — CORS 처리 변경 없음. `TRADING_SYSTEM_CORS_ALLOW_ORIGINS` env-var로 Vercel URL 추가로 충분.
- `src/trading_system/api/routes/analytics.py` — `_RUN_REPOSITORY` 임포트 변경 없음. `backtest.py` factory 교체로 자동 적용.
- `src/trading_system/app/services.py` — `equity_writer`, `run_repository` 필드 추가 없음. 기존 구조 유지.
- `frontend/store/apiStore.ts` — `NEXT_PUBLIC_API_BASE_URL` 사용 변경 없음.
- `frontend/lib/api/client.ts` — 변경 없음.

## Delivery Slices

### Slice 0. 의존성 추가 + EquityWriter Protocol 분리

- `psycopg[binary]>=3.1` 의존성 추가
- `EquityWriterProtocol` 추가 (`session_id`, `append`, `read_recent`)
- `EquityWriter` → `FileEquityWriter` rename + alias
- `loop.py` 타입 힌트 보강

### Slice 1. SQL 마이그레이션 + Supabase Repository 구현

- 마이그레이션 SQL 파일 작성
- `SupabaseBacktestRunRepository` 구현 + mock 단위 테스트
- `SupabaseEquityWriter` 구현 + mock 단위 테스트

### Slice 2. 저장소 전환 경로 통합

- `backtest.py` `_create_run_repository()` factory
- `LiveTradingLoop` 생성 시 EquityWriter 분기
- 기존 테스트 격리 확인
- 전체 pytest PASS 확인

### Slice 3. Railway 배포 설정

- `server.py` `app = create_app()` 모듈 전역 추가
- `Dockerfile` + `railway.json`
- `GET /health` 엔드포인트 확인/추가
- `.env.example` 확장

### Slice 4. Vercel 배포 설정

- `frontend/.env.local.example` 보강
- Vercel 배포 가이드 (README)

### Slice 5. GitHub Actions CI

- `.github/workflows/ci.yml` 작성

### Slice 6. 통합 검증 및 문서

- 전체 회귀 테스트 실행
- README 배포 가이드 갱신

## Success Metrics

- `DATABASE_URL` 설정 시 `SupabaseBacktestRunRepository`가 `_RUN_REPOSITORY`로 선택되어 Supabase에 런 데이터가 저장된다
- `DATABASE_URL` 미설정 시 기존 `FileBacktestRunRepository`가 선택되어 로컬 동작이 유지된다
- `analytics.py`의 `_RUN_REPOSITORY`가 `backtest.py` factory를 통해 자동 교체된다
- `SupabaseEquityWriter.session_id` 속성이 `GET /api/v1/dashboard/equity` 응답에 정상 반영된다
- `Dockerfile`로 이미지 빌드 성공, `uvicorn trading_system.api.server:app`으로 컨테이너 기동 성공
- Railway 배포 후 `GET /health` 200 응답
- Railway 배포 후 `GET /api/v1/dashboard/stream` SSE 연결이 정상 동작
- Vercel 배포 후 `NEXT_PUBLIC_API_BASE_URL`이 Railway URL로 설정되어 API 요청 성공
- `TRADING_SYSTEM_CORS_ALLOW_ORIGINS`에 Vercel URL 추가 시 CORS 오류 없이 연동
- GitHub Actions CI가 `push`/`PR` 이벤트에 트리거되어 pytest + ruff + frontend build 검증
- `pytest` 전체 테스트 PASS (기존 221개 이상)
- `ruff check src/ tests/` 0 errors
- `npx tsc --noEmit` PASS, `npm run lint` PASS, `npm run build` PASS

## Risks and Follow-up

- psycopg3 동기 드라이버를 사용하므로 FastAPI의 비동기 엔드포인트에서 DB 호출 시 이벤트 루프를 블로킹할 수 있다. 현재 백엔드 엔드포인트가 동기 방식(`def`)이면 FastAPI가 threadpool에서 실행하므로 문제없으나, 향후 비동기 전환 시 `asyncpg` 또는 `psycopg3 async` 드라이버로 교체가 필요하다.
- Supabase 무료 플랜은 비활성 프로젝트를 1주일 후 일시 정지한다. 운영 전환 시 유료 플랜 필요.
- Railway 무료 플랜은 월 500시간 제한이 있다. 지속 운영 시 유료 플랜 필요.
- SSE 연결(`/api/v1/dashboard/stream`)은 Railway에서 정상 동작하지만, CORS 설정이 올바르지 않으면 Vercel 프론트에서 연결 거부된다. `TRADING_SYSTEM_CORS_ALLOW_ORIGINS`에 Vercel URL 정확히 입력 필요 (트레일링 슬래시 없이).
- `BacktestRunDTO`의 `result` 필드(`BacktestResultDTO`)는 중첩 dataclass 구조로, JSONB 직렬화/역직렬화 시 타입 복원 로직이 `FileBacktestRunRepository`와 동일하게 필요하다. 기존 직렬화 코드를 공통 헬퍼로 추출하여 재사용한다.
- GitHub Actions에서 `DATABASE_URL` 없이 CI가 통과해야 한다. Supabase 관련 테스트는 `pytest.mark.skipif(not os.environ.get("DATABASE_URL"), ...)` 로 skip 처리한다.
- `equity_snapshots` 테이블은 장기 실행 시 레코드가 계속 증가한다. Phase 10에서 오래된 스냅샷 자동 삭제(TTL) 또는 파티셔닝을 검토한다.
- `_RUN_REPOSITORY` 모듈 전역 factory는 모듈 임포트 시점에 `DATABASE_URL`을 읽는다. 테스트에서 env-var를 monkeypatch할 때는 모듈 리로드 또는 `_RUN_REPOSITORY` 자체를 monkeypatch해야 한다. 기존 테스트가 이미 `_RUN_REPOSITORY`를 monkeypatch하는 패턴을 사용하므로 영향 없다.
