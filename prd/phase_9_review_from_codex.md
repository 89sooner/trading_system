# Verification Result

## 1. Target checked

`prd/phase_9_prd.md`, `prd/phase_9_implementation_plan.md`, `prd/phase_9_task.md`를 기준으로 현재 변경사항이 Phase 9 목표를 충족하는지 검증했다.

검증 기준은 다음이었다.

- Supabase 기반 런 저장소와 equity writer가 실제 코드 경로에 연결되었는가
- Railway 배포 최소 산출물(`Dockerfile`, `railway.json`, `/health`)이 준비되었는가
- CI 산출물이 추가되었는가
- Phase 9 문서가 요구한 프론트 배포/환경변수/문서화/CORS 작업이 실제로 반영되었는가
- 관련 테스트와 lint가 통과하는가

## 2. What was inspected

- `pyproject.toml`
- `.env.example`
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/server.py`
- `src/trading_system/app/equity_writer.py`
- `src/trading_system/app/services.py`
- `src/trading_system/app/supabase_equity_writer.py`
- `src/trading_system/backtest/supabase_repository.py`
- `scripts/migrations/001_create_backtest_runs.sql`
- `scripts/migrations/002_create_equity_snapshots.sql`
- `.github/workflows/ci.yml`
- `Dockerfile`
- `railway.json`
- `tests/unit/test_supabase_repository.py`
- `tests/unit/test_supabase_equity_writer.py`
- `tests/integration/test_run_persistence_integration.py`
- `README.md`
- `frontend/README.md`
- `frontend/store/apiStore.ts`
- 작업 트리 상태와 변경 파일 목록

## 3. Validation evidence

- `git status --short`
  결과: Phase 9 관련 백엔드/배포 파일 외에 `src/trading_system/integrations/kis.py`, 여러 KIS 테스트, `tests/unit/test_core_ops.py`, `tests/unit/test_execution_adapters_and_broker.py` 등 비직접 관련 변경도 존재했다.

- `git diff -- pyproject.toml .env.example src/trading_system/app/equity_writer.py src/trading_system/app/services.py src/trading_system/api/routes/backtest.py src/trading_system/api/server.py src/trading_system/app/supabase_equity_writer.py src/trading_system/backtest/supabase_repository.py tests/unit/test_supabase_equity_writer.py tests/unit/test_supabase_repository.py tests/integration/test_run_persistence_integration.py .github/workflows/ci.yml Dockerfile railway.json scripts/migrations`
  결과: `DATABASE_URL` 도입, Supabase repository/writer 추가, `_RUN_REPOSITORY` env-aware factory 전환, `/health` 추가, Docker/Railway/CI/migration 파일 추가를 확인했다.

- `python -c "import psycopg; print(psycopg.__version__)"`
  결과: `3.3.3`

- `ruff check src/trading_system/backtest/supabase_repository.py src/trading_system/app/supabase_equity_writer.py src/trading_system/app/equity_writer.py src/trading_system/app/services.py src/trading_system/api/routes/backtest.py src/trading_system/api/server.py tests/unit/test_supabase_repository.py tests/unit/test_supabase_equity_writer.py tests/integration/test_run_persistence_integration.py`
  결과: `All checks passed!`

- `pytest tests/unit/test_supabase_repository.py -q`
  결과: `10 passed, 1 skipped in 0.15s`

- `pytest tests/unit/test_supabase_equity_writer.py -q`
  결과: `5 passed, 1 skipped in 0.10s`

- `pytest tests/integration/test_run_persistence_integration.py -vv`
  결과: 첫 테스트 `test_run_persists_across_repository_recreation` 시작 후 완료되지 않았다.

- `timeout 15 pytest tests/integration/test_run_persistence_integration.py::test_run_persists_across_repository_recreation -vv`
  결과: 15초 내 종료되지 않아 exit code `124`로 중단되었다.

- `rg --files -g 'frontend/vercel.json' -g 'frontend/.env.example' -g 'frontend/.env.local.example' -g 'README.md' -g '.github/workflows/ci.yml' -g 'Dockerfile' -g 'railway.json'`
  결과: `Dockerfile`, `railway.json`, `README.md`, `frontend/README.md`, `frontend/.env.local.example`는 존재하지만 `frontend/vercel.json`, `frontend/.env.example`는 없었다.

- `rg -n "DATABASE_URL|TRADING_SYSTEM_CORS|NEXT_PUBLIC_API_BASE_URL|NEXT_PUBLIC_API_URL|NEXT_PUBLIC_API_KEY|vercel" frontend README.md src/trading_system .env.example -g '!frontend/node_modules/**'`
  결과: 프론트는 계속 `NEXT_PUBLIC_API_BASE_URL`을 사용하고 있었고, CORS는 여전히 `TRADING_SYSTEM_CORS_ALLOW_ORIGINS` 기반이며, `NEXT_PUBLIC_API_URL`/`NEXT_PUBLIC_API_KEY` 전환은 확인되지 않았다.

- `git diff -- README.md frontend .github/workflows/ci.yml Dockerfile railway.json .env.example | sed -n '1,260p'`
  결과: README와 frontend 문서에는 Phase 9 배포 가이드 갱신이 없었고, `.env.example`에는 `DATABASE_URL`만 추가되었다.

## 4. Decision

- Needs fix

## 5. Findings

- High: Phase 9 핵심 백엔드 저장소 전환은 부분적으로 구현되었다.
  `src/trading_system/api/routes/backtest.py`가 이제 `DATABASE_URL` 존재 시 `SupabaseBacktestRunRepository`를 선택하므로, 이전 계획 리뷰에서 지적했던 `_RUN_REPOSITORY` 경로 누락은 이번 변경에서 보완되었다.

- High: Supabase 관련 단위 검증은 통과했지만 기존 run persistence 통합 검증이 완료되지 않는다.
  `tests/integration/test_run_persistence_integration.py`는 첫 테스트에서 15초 내 종료되지 않았다. 이는 Phase 9 목표가 “기존 동작 유지 + 저장소 전환”인 점을 고려하면 미해결 검증 이슈다.

- High: Phase 9 문서가 요구한 프론트 배포 산출물이 빠져 있다.
  `frontend/vercel.json`과 `frontend/.env.example`는 존재하지 않는다. 현재 프론트는 여전히 `frontend/store/apiStore.ts`의 `NEXT_PUBLIC_API_BASE_URL`을 사용하며, 문서에 적힌 `NEXT_PUBLIC_API_URL`/`NEXT_PUBLIC_API_KEY` 기준 구현은 확인되지 않았다.

- High: CORS 동적 설정 작업은 사실상 미구현이다.
  현재 동작은 여전히 `src/trading_system/api/security.py`의 `TRADING_SYSTEM_CORS_ALLOW_ORIGINS` 기반이며, 문서에서 상정한 추가 CORS 구현이나 env name 정리는 반영되지 않았다.

- Medium: Railway 배포 최소 산출물은 준비되었다.
  `Dockerfile`, `railway.json`, `src/trading_system/api/server.py`의 `/health`, module-level `app`가 추가되어 backend 배포 시작점은 이전보다 현실적이다.

- Medium: `.env.example` 확장은 부분 완료에 그친다.
  `DATABASE_URL`은 추가되었지만, Phase 9 task에서 명시한 `TRADING_SYSTEM_RUNS_DIR`, `TRADING_SYSTEM_EQUITY_DIR`, webhook 관련 값 보강과 배포 순서 문서화 수준까지는 도달하지 못했다.

- Medium: 문서화 작업은 미완료다.
  `README.md`에 Supabase → Railway → Vercel 배포 가이드가 추가되지 않았고, bilingual update requirement를 만족하는 변경도 없었다.

- Medium: scope drift가 있다.
  현재 tracked diff에는 `src/trading_system/integrations/kis.py`와 여러 KIS/ops 테스트 변경이 포함되어 있다. 이들은 Phase 9 핵심 산출물과 직접 연결되지 않는다.

## 6. Scope compliance

- 계획과 일치하는 항목
  - `psycopg[binary]` 의존성 추가
  - `SupabaseBacktestRunRepository` 구현
  - `SupabaseEquityWriter` 구현
  - `EquityWriter` 추상화에 `session_id` 포함
  - `_RUN_REPOSITORY` 경로에 `DATABASE_URL` 분기 추가
  - `Dockerfile`, `railway.json`, `/health`, CI workflow 추가
  - SQL migration 파일 추가

- 계획과 불일치하거나 미완료인 항목
  - `frontend/vercel.json` 없음
  - `frontend/.env.example` 없음
  - README 배포 가이드 없음
  - CORS 작업이 문서상 목표와 다르게 그대로 유지됨
  - 프론트 env 전략이 문서의 `NEXT_PUBLIC_API_URL` 기준과 맞지 않음
  - 전체 회귀 검증이 완료되지 않음

- 계획 외 변경
  - KIS 관련 구현/테스트 변경
  - core ops / execution adapter 테스트 변경

## 7. Remaining risks or unknowns

- `test_run_persistence_integration.py`가 멈추는 원인이 확인되지 않았다.
  현재 변경이 기존 API backtest flow를 block하거나, 테스트 환경에서 `create_app()`와 repository 조합에 새로운 대기 상태를 만들었을 가능성이 있다.

- Docker 실제 빌드는 이번 검증에서 수행하지 않았다.
  파일 내용은 합리적이지만, 이미지 빌드 성공은 아직 미검증이다.

- Supabase 실환경 round-trip은 skip 상태였다.
  `DATABASE_URL`이 없는 환경이라 integration-style DB 검증은 확인하지 못했다.

- CI workflow는 파일은 추가되었지만 GitHub Actions에서 실제 실행된 증적은 없다.

- 프론트 배포 구성이 비어 있으므로 Vercel 연동 관점에서는 Phase 9 목적을 아직 달성하지 못했다.

## 8. Next loop handoff

Goal:
Phase 9를 문서 목표 수준으로 마무리하고, 멈추는 persistence 통합 검증을 정상화한다.

Why another loop is needed:
현재 상태는 backend 저장소 전환의 일부만 완료되었고, 프론트 배포 산출물·CORS 정리·README 배포 문서·통합 검증이 빠져 있어 Phase 9를 완료로 판정할 수 없다.

Files likely in scope:
- `tests/integration/test_run_persistence_integration.py`
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/server.py`
- `src/trading_system/api/security.py`
- `README.md`
- `frontend/store/apiStore.ts`
- `frontend/vercel.json`
- `frontend/.env.example` 또는 현재 env 문서 체계에 맞는 대응 파일
- `.env.example`

Known issues:
- persistence integration test가 15초 내 완료되지 않음
- `frontend/vercel.json`, `frontend/.env.example` 미존재
- README 배포 가이드 미작성
- CORS 계획 미반영
- Phase 9와 무관한 KIS/ops 테스트 변경이 섞여 있음

Validation to rerun:
- `pytest tests/integration/test_run_persistence_integration.py -q`
- `pytest tests/unit/test_api_server.py -q`
- `ruff check src/ tests/`
- `pytest tests/unit/test_supabase_repository.py tests/unit/test_supabase_equity_writer.py -q`
- 필요 시 `docker build -t trading-system .`
