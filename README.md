# trading_system / 트레이딩 시스템

> **Language policy / 언어 정책**
>
> - **EN:** This README is maintained in both English and Korean with the same level of detail. Any future README updates must be reflected in **both languages**.
> - **KO:** 이 README는 영어/한국어를 **동일한 수준의 상세도**로 유지합니다. 앞으로 README를 수정할 때는 **두 언어 모두** 반드시 함께 업데이트해야 합니다.
> - **EN:** All operator-facing documents under `docs/` must also have both English and Korean versions. Use `.ko.md` for Korean companions of English originals, and `.en.md` for English companions of Korean originals when needed.
> - **KO:** `docs/` 아래의 운영자 대상 문서도 모두 영어/한국어 버전을 함께 유지합니다. 영어 원문에는 `.ko.md` 한국어 대응 문서를, 한국어 원문에는 필요 시 `.en.md` 영어 대응 문서를 둡니다.

---

## 1) Project overview / 프로젝트 개요

### EN

`trading_system` is a modular Python trading workspace focused on deterministic backtesting, clear service boundaries, and safe evolution toward production-like operations.

Current emphasis:

- deterministic backtest orchestration
- explicit boundaries across strategy/risk/execution/portfolio/analytics
- structured logging + resilience helpers
- testability without live infrastructure

### KO

`trading_system`은 결정적 백테스트, 명확한 서비스 경계, 실서비스 확장을 위한 안전한 진화를 목표로 하는 모듈형 Python 트레이딩 워크스페이스입니다.

현재 중점:

- 결정적(backtest deterministic) 오케스트레이션
- strategy/risk/execution/portfolio/analytics 레이어 분리
- 구조화 로깅 + 복원력 유틸
- 라이브 인프라 없이도 높은 테스트 가능성

---

## 2) Goals / 목표

### EN

- Separate market data, strategy, risk, execution, portfolio, backtest, and analytics concerns.
- Keep domain logic testable without live infrastructure.
- Enable smooth growth from local research to production-like service architecture.

### KO

- 시장데이터, 전략, 리스크, 실행, 포트폴리오, 백테스트, 분석의 관심사를 분리합니다.
- 라이브 인프라 없이도 도메인 로직을 테스트 가능하게 유지합니다.
- 로컬 연구 환경에서 운영형 서비스 구조로 자연스럽게 확장할 수 있도록 설계합니다.

---

## 3) Repository layout / 저장소 구조

```text
src/trading_system/
  analytics/
  app/
  backtest/
  config/
  core/
  data/
  execution/
  patterns/
  portfolio/
  risk/
  strategy/

tests/
docs/
configs/
examples/
.codex/skills/
.opencode/skills/
```

---

## 4) Quick start / 빠른 시작

### EN

```bash
uv venv --python 3.12 --seed .venv
uv pip install --python .venv/bin/python -e '.[dev]'
uv run --python .venv/bin/python --no-sync pytest
```

### KO

```bash
uv venv --python 3.12 --seed .venv
uv pip install --python .venv/bin/python -e '.[dev]'
uv run --python .venv/bin/python --no-sync pytest
```

---

## 5) Run commands / 실행 명령

### 5.1 One-command local run / 원커맨드 로컬 실행

### EN

```bash
./scripts/run_engine.sh backtest
./scripts/run_engine.sh live-preflight
```

- The script auto-creates `.venv` and installs dependencies on first run.
- Set `TRADING_SYSTEM_SYNC_DEPS=1` to force a dependency resync before running.
- The workflow assumes `uv` is installed and available on your `PATH` (the scripts also fall back to `~/.local/bin/uv`).
- The scripts use a project-local `UV_CACHE_DIR=.uv-cache` so they work even when the home cache directory is restricted.
- `live-preflight` uses `TRADING_SYSTEM_API_KEY` from your environment when available; otherwise it injects a local dummy key for preflight only.

### KO

```bash
./scripts/run_engine.sh backtest
./scripts/run_engine.sh live-preflight
```

- 스크립트는 첫 실행 시 `.venv`를 자동 생성하고 의존성을 설치한 뒤 CLI를 실행합니다.
- 실행 전에 의존성을 다시 동기화하려면 `TRADING_SYSTEM_SYNC_DEPS=1`을 지정하세요.
- 실행 흐름은 `uv`가 PATH에 있음을 전제로 하며, 없으면 `~/.local/bin/uv`를 대신 찾습니다.
- 홈 캐시 디렉터리가 제한된 환경에서도 동작하도록 스크립트는 프로젝트 로컬 `UV_CACHE_DIR=.uv-cache`를 사용합니다.
- `live-preflight`는 환경변수 `TRADING_SYSTEM_API_KEY`가 있으면 사용하고, 없으면 프리플라이트 전용 더미 키를 주입합니다.

### 5.2 Test subsets / 테스트 세트

### EN

- Fast smoke set: `uv run --python .venv/bin/python --no-sync pytest -m smoke -q`
- Extended set: `uv run --python .venv/bin/python --no-sync pytest -m "not smoke" -q`

### KO

- 빠른 스모크 세트: `uv run --python .venv/bin/python --no-sync pytest -m smoke -q`
- 확장 세트: `uv run --python .venv/bin/python --no-sync pytest -m "not smoke" -q`

### 5.3 Backtest mode / 백테스트 모드

```bash
TRADING_SYSTEM_ENV=local TRADING_SYSTEM_TIMEZONE=Asia/Seoul \
uv run --python .venv/bin/python --no-sync -m trading_system.app.main --mode backtest --symbols BTCUSDT
```

### 5.4 Backtest mode (KRX CSV example) / 백테스트 모드 (KRX CSV 예시)

```bash
mkdir -p data/market
cat > data/market/005930.csv <<'CSV'
timestamp,open,high,low,close,volume
2024-01-02T00:00:00+00:00,70000,70500,69900,70400,1000
2024-01-03T00:00:00+00:00,70400,71000,70300,70900,1200
CSV

TRADING_SYSTEM_ENV=local TRADING_SYSTEM_TIMEZONE=Asia/Seoul \
TRADING_SYSTEM_CSV_DIR=data/market \
uv run --python .venv/bin/python --no-sync -m trading_system.app.main --mode backtest --provider csv --symbols 005930 --trade-quantity 1
```

### 5.5 Live preflight mode (default, no order submission) / 라이브 프리플라이트 모드 (기본값, 실주문 없음)

KIS credentials can be kept in a local `.env` file. Copy the tracked template,
then replace only the values in your untracked `.env`. `trading_system.app.main`
and the API server load `.env` automatically without overwriting shell exports.

KIS 인증정보는 로컬 `.env` 파일에 둘 수 있습니다. 추적되는 템플릿을 복사한 뒤,
추적되지 않는 `.env` 안의 값만 교체하세요. CLI와 API 서버는 `.env`를 자동
로드하며, 이미 셸에 export된 값은 덮어쓰지 않습니다.

```bash
cp .env.example .env
```

```bash
TRADING_SYSTEM_ENV=local TRADING_SYSTEM_TIMEZONE=Asia/Seoul \
TRADING_SYSTEM_API_KEY=dummy-key \
uv run --python .venv/bin/python --no-sync -m trading_system.app.main --mode live --symbols BTCUSDT
```

```bash
TRADING_SYSTEM_ENV=local TRADING_SYSTEM_TIMEZONE=Asia/Seoul \
TRADING_SYSTEM_KIS_ENV=prod \
TRADING_SYSTEM_KIS_MARKET_DIV=J \
TRADING_SYSTEM_KIS_APP_KEY=your-app-key \
TRADING_SYSTEM_KIS_APP_SECRET=your-app-secret \
TRADING_SYSTEM_KIS_CANO=12345678 \
TRADING_SYSTEM_KIS_ACNT_PRDT_CD=01 \
uv run --python .venv/bin/python --no-sync -m trading_system.app.main --mode live --provider kis --broker kis --symbols 005930
```

### 5.6 Live paper mode (explicit opt-in) / 라이브 페이퍼 모드 (명시적 활성화)

```bash
TRADING_SYSTEM_ENV=local TRADING_SYSTEM_TIMEZONE=Asia/Seoul \
TRADING_SYSTEM_API_KEY=dummy-key \
uv run --python .venv/bin/python --no-sync -m trading_system.app.main --mode live --symbols BTCUSDT --live-execution paper
```

### 5.7 Live order mode (explicit opt-in + KIS only) / 라이브 실주문 모드 (명시적 활성화 + KIS 전용)

```bash
TRADING_SYSTEM_ENV=local TRADING_SYSTEM_TIMEZONE=Asia/Seoul \
TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true \
TRADING_SYSTEM_LIVE_BAR_SAMPLES=2 \
TRADING_SYSTEM_KIS_ENV=prod \
TRADING_SYSTEM_KIS_MARKET_DIV=J \
TRADING_SYSTEM_KIS_APP_KEY=your-app-key \
TRADING_SYSTEM_KIS_APP_SECRET=your-app-secret \
TRADING_SYSTEM_KIS_CANO=12345678 \
TRADING_SYSTEM_KIS_ACNT_PRDT_CD=01 \
uv run --python .venv/bin/python --no-sync -m trading_system.app.main --mode live --provider kis --broker kis --symbols 005930 --live-execution live
```

For the full KIS live environment template, paper rehearsal checklist, and first real-order gate, use `docs/runbooks/kis-domestic-live-operations.md` / `docs/runbooks/kis-domestic-live-operations.ko.md`.

### 5.8 Built-in backtest example / 내장 백테스트 예시

```bash
uv run --python .venv/bin/python --no-sync -m trading_system.backtest.example
```

### 5.9 HTTP API mode / HTTP API 모드

### EN

Always run the API through `uv` against the project virtualenv. Avoid calling system `uvicorn` directly because it may use a different Python environment.

Verify your environment first:

```bash
uv --version
cat .python-version
uv pip show --python .venv/bin/python fastapi uvicorn
```

Run API server:

```bash
UV_CACHE_DIR=.uv-cache uv run --python .venv/bin/python --no-sync -m uvicorn trading_system.api.server:create_app --factory --host 0.0.0.0 --port 8000
```

Request examples:

```bash
TRADING_SYSTEM_ALLOWED_API_KEYS=dummy-key \
curl -X POST http://127.0.0.1:8000/api/v1/backtests \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dummy-key" \
  -d '{"mode":"backtest","symbols":["BTCUSDT"],"provider":"mock","broker":"paper","live_execution":"preflight","risk":{"max_position":"1","max_notional":"100000","max_order_size":"0.25"},"backtest":{"starting_cash":"10000","fee_bps":"5","trade_quantity":"0.1"}}'

curl http://127.0.0.1:8000/api/v1/backtests/<run_id> -H "X-API-Key: dummy-key"

TRADING_SYSTEM_ALLOWED_API_KEYS=dummy-key TRADING_SYSTEM_API_KEY=dummy-key \
curl -X POST http://127.0.0.1:8000/api/v1/live/preflight \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dummy-key" \
  -d '{"mode":"live","symbols":["BTCUSDT"],"provider":"mock","broker":"paper","live_execution":"preflight","risk":{"max_position":"1","max_notional":"100000","max_order_size":"0.25"},"backtest":{"starting_cash":"10000","fee_bps":"5","trade_quantity":"0.1"}}'
```

Validation failures are returned as 4xx (`settings_validation_error` or `invalid_*`), and runtime failures are returned as a structured 5xx body (`runtime_error` or `internal_server_error`). Authentication failures return `auth_invalid_api_key`, and excessive traffic returns `rate_limit_exceeded`.
The same endpoint accepts `live_execution=live` when KIS runtime guards are satisfied.
`GET /health` is intentionally unauthenticated so load balancers and Railway-style health checks can probe the service without an API key.

Live runtime orchestration is API-owned:

- `GET /api/v1/dashboard/status` returns controller state even when no loop is active.
- `POST /api/v1/live/runtime/start` launches one live session after re-running preflight on the server and returns the exact structured preflight snapshot used for that start attempt.
- `GET /api/v1/live/runtime/sessions` supports historical session filters (`start`, `end`, `provider`, `broker`, `live_execution`, `state`, `symbol`, `has_error`) plus pagination, and `/api/v1/live/runtime/sessions/export` returns bounded CSV/JSONL exports.
- `GET /api/v1/live/runtime/sessions/<session_id>/evidence` combines session metadata, order-audit summary, archived runtime incidents, and equity point count for post-run review.
- `POST /api/v1/dashboard/control` now supports `pause`, `resume`, `reset`, and `stop`.
- Only one live session may be active per API process at a time.

Backtest API execution is asynchronous:

- `POST /api/v1/backtests` returns `202 Accepted` with `status="queued"`.
- Poll `GET /api/v1/backtests/<run_id>` until the run reaches `succeeded`, `failed`, or `cancelled`.
- Pending runs may report `queued` or `running` with `result=null`, `finished_at=null`, and a `job` block containing worker lease, heartbeat, progress, and cancel state.
- `POST /api/v1/backtests/<run_id>/cancel` requests cooperative cancellation for queued or running jobs.
- The API-owned dispatcher uses the same durable job contract as the standalone worker. Run `python -m trading_system.app.backtest_worker --once` for a one-job worker smoke test, or omit `--once` for a polling worker process.
- For a repeatable local worker process check, run `python scripts/backtest_worker_smoke.py`; it creates a temporary durable job, processes it in a separate worker process, and verifies terminal `succeeded` status with 100% progress.
- `GET /api/v1/analytics/backtests/<run_id>/trades` returns `409` until the run has succeeded.

Visualization response example (fixed schema):

```json
{
  "result": {
    "summary": {
      "return": "0.0125",
      "max_drawdown": "-0.0340",
      "volatility": "0.0217",
      "win_rate": "0.5714"
    },
    "equity_curve": [
      { "timestamp": "2024-01-01T00:00:00Z", "equity": "10000" },
      { "timestamp": "2024-01-02T00:00:00Z", "equity": "10125" }
    ],
    "drawdown_curve": [
      { "timestamp": "2024-01-01T00:00:00Z", "drawdown": "0" },
      { "timestamp": "2024-01-02T00:00:00Z", "drawdown": "0" }
    ],
    "orders": [
      {
        "event": "order.filled",
        "payload": { "symbol": "BTCUSDT", "filled_quantity": "0.1", "status": "filled" }
      }
    ],
    "risk_rejections": [
      {
        "event": "risk.rejected",
        "payload": { "symbol": "BTCUSDT", "requested_quantity": "0.5" }
      }
    ]
  }
}
```

### KO

API 서버는 반드시 프로젝트 가상환경을 가리키는 `uv` 경유로 실행하세요. 시스템 전역 `uvicorn`을 직접 호출하면 다른 Python 환경을 타서 의존성을 못 찾을 수 있습니다.

먼저 환경을 확인하세요:

```bash
uv --version
cat .python-version
uv pip show --python .venv/bin/python fastapi uvicorn
```

API 서버 실행:

```bash
UV_CACHE_DIR=.uv-cache uv run --python .venv/bin/python --no-sync -m uvicorn trading_system.api.server:create_app --factory --host 0.0.0.0 --port 8000
```

호출 예시:

```bash
TRADING_SYSTEM_ALLOWED_API_KEYS=dummy-key \
curl -X POST http://127.0.0.1:8000/api/v1/backtests \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dummy-key" \
  -d '{"mode":"backtest","symbols":["BTCUSDT"],"provider":"mock","broker":"paper","live_execution":"preflight","risk":{"max_position":"1","max_notional":"100000","max_order_size":"0.25"},"backtest":{"starting_cash":"10000","fee_bps":"5","trade_quantity":"0.1"}}'

curl http://127.0.0.1:8000/api/v1/backtests/<run_id> -H "X-API-Key: dummy-key"

TRADING_SYSTEM_ALLOWED_API_KEYS=dummy-key TRADING_SYSTEM_API_KEY=dummy-key \
curl -X POST http://127.0.0.1:8000/api/v1/live/preflight \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dummy-key" \
  -d '{"mode":"live","symbols":["BTCUSDT"],"provider":"mock","broker":"paper","live_execution":"preflight","risk":{"max_position":"1","max_notional":"100000","max_order_size":"0.25"},"backtest":{"starting_cash":"10000","fee_bps":"5","trade_quantity":"0.1"}}'
```

입력 검증 실패는 4xx(`settings_validation_error` 또는 `invalid_*`)로, 실행 중 오류는 구조화된 5xx(`runtime_error` 또는 `internal_server_error`)로 반환합니다. 인증 실패는 `auth_invalid_api_key`, 과도한 요청은 `rate_limit_exceeded`로 반환됩니다.
동일 엔드포인트에서 KIS 가드 조건을 만족하면 `live_execution=live`도 허용됩니다.
`GET /health`는 로드밸런서와 Railway 같은 헬스체크가 API 키 없이 호출할 수 있도록 인증 예외 경로로 유지됩니다.

라이브 런타임 orchestration은 API가 직접 소유합니다.

- `GET /api/v1/dashboard/status`는 active loop가 없어도 controller 상태를 반환합니다.
- `POST /api/v1/live/runtime/start`는 서버에서 preflight를 다시 수행한 뒤 단일 live session을 시작합니다.
- `GET /api/v1/live/runtime/sessions`는 `start`, `end`, `provider`, `broker`, `live_execution`, `state`, `symbol`, `has_error` 필터와 pagination을 지원하며, `/api/v1/live/runtime/sessions/export`는 bounded CSV/JSONL export를 반환합니다.
- `GET /api/v1/live/runtime/sessions/<session_id>/evidence`는 session metadata, order audit 요약, archived runtime incident, equity point count를 session id 기준으로 묶어 반환합니다.
- `POST /api/v1/dashboard/control`은 이제 `pause`, `resume`, `reset`, `stop`을 지원합니다.
- 한 API 프로세스 안에서 동시에 하나의 live session만 허용됩니다.

백테스트 API는 비동기 실행 모델을 사용합니다.

- `POST /api/v1/backtests`는 `202 Accepted`와 `status="queued"`를 반환합니다.
- 이후 `GET /api/v1/backtests/<run_id>`를 polling 하여 `succeeded` 또는 `failed`에 도달했는지 확인합니다.
- 진행 중 run은 `queued` 또는 `running` 상태이며, 이때 `result=null`, `finished_at=null`일 수 있습니다.
- `GET /api/v1/analytics/backtests/<run_id>/trades`는 run이 성공 완료되기 전까지 `409`를 반환합니다.

시각화 응답 예시(고정 스키마):

```json
{
  "result": {
    "summary": {
      "return": "0.0125",
      "max_drawdown": "-0.0340",
      "volatility": "0.0217",
      "win_rate": "0.5714"
    },
    "equity_curve": [
      { "timestamp": "2024-01-01T00:00:00Z", "equity": "10000" },
      { "timestamp": "2024-01-02T00:00:00Z", "equity": "10125" }
    ],
    "drawdown_curve": [
      { "timestamp": "2024-01-01T00:00:00Z", "drawdown": "0" },
      { "timestamp": "2024-01-02T00:00:00Z", "drawdown": "0" }
    ],
    "orders": [
      {
        "event": "order.filled",
        "payload": { "symbol": "BTCUSDT", "filled_quantity": "0.1", "status": "filled" }
      }
    ],
    "risk_rejections": [
      {
        "event": "risk.rejected",
        "payload": { "symbol": "BTCUSDT", "requested_quantity": "0.5" }
      }
    ]
  }
}
```

Build note: `frontend/package.json` uses `next build --webpack` because the default Turbopack build path can fail in restricted sandbox/process environments while the webpack path remains stable for CI and production packaging.

### 5.10 Frontend + backend local development / 프론트엔드 + 백엔드 로컬 개발

### EN

The repository now includes a Next.js frontend under `frontend/`. Current user-facing routes are:

- `/`: create a new backtest run with optional strategy profile selection
- `/patterns`: train, preview, save, and list pattern sets
- `/patterns/$patternSetId`: inspect one saved pattern set
- `/strategies`: create and list strategy profiles
- `/runs` and `/runs/$runId`: inspect run history, result charts, signals, fills, rejections, and trade analytics
- `/dashboard`: inspect controller state, live loop status, positions, recent events, equity history, SSE connectivity, and control actions (`pause`, `resume`, `reset`, `stop`)
- `/admin`: create, list, and revoke API keys through the browser

**One-stop script (recommended):**

```bash
./scripts/run_all.sh            # Start both backend API + frontend dev server
./scripts/run_all.sh --backend  # Backend only
./scripts/run_all.sh --frontend # Frontend only
```

- The script auto-creates `.venv`, installs Python/npm dependencies on first run, copies `.env.local` from the example file, and starts both servers in a single process.
- Backend defaults to port `8000`, frontend to port `3000`. Override with `API_PORT` and `FRONTEND_PORT` environment variables.
- Press `Ctrl+C` to stop all services.

**Manual two-terminal alternative:**

```bash
# Terminal A: backend API
UV_CACHE_DIR=.uv-cache uv run --python .venv/bin/python --no-sync -m uvicorn trading_system.api.server:create_app --factory --host 0.0.0.0 --port 8000

# Terminal B: frontend dev server
cd frontend && npm install && npm run dev
```

Open `http://localhost:3000/`.

If your backend runs on a different port (for example `9000`), set the **API Base URL** field in the frontend UI to:

```text
http://127.0.0.1:9000/api/v1
```

Local development flow:

1. Start backend API server.
2. Start frontend dev server.
3. Open `/patterns` to train and save a pattern set.
4. Open `/strategies` to create a strategy profile.
5. Open `/` to submit a backtest run.
6. Open `/runs` and `/runs/<run_id>` to review results and trade analytics.
7. Open `/dashboard` to inspect an attached live loop.

API endpoint contract used by the frontend client:

- `POST /api/v1/backtests` and `GET /api/v1/backtests/{run_id}`
- `GET /api/v1/analytics/backtests/{run_id}/trades`
- `POST /api/v1/patterns/train`
- `POST /api/v1/patterns`
- `GET /api/v1/patterns` and `GET /api/v1/patterns/{pattern_set_id}`
- `POST /api/v1/strategies`
- `GET /api/v1/strategies` and `GET /api/v1/strategies/{strategy_id}`
- `GET /api/v1/dashboard/status`
- `GET /api/v1/dashboard/positions`
- `GET /api/v1/dashboard/events`
- `GET /api/v1/dashboard/equity`
- `GET /api/v1/dashboard/stream` (SSE, optional `api_key` query parameter)
- `POST /api/v1/dashboard/control`
- `GET /api/v1/admin/keys`, `POST /api/v1/admin/keys`, `DELETE /api/v1/admin/keys/{key_id}`

Frontend error handling is separated by path:

- Network failure: backend not reachable
- 4xx failure: validation/input issue from API
- 5xx failure: runtime/internal server issue

The dashboard now exposes controller state even when no live loop is active. Operators can start one live paper/live session from the UI through `POST /api/v1/live/runtime/start`, and an already-attached external loop still remains a supported compatibility path.

### KO

저장소에는 `frontend/` 경로의 Next.js 프론트엔드가 포함되어 있습니다. 현재 사용자 진입 라우트는 다음과 같습니다.

- `/`: 전략 프로필 선택을 포함한 신규 백테스트 실행
- `/patterns`: 패턴셋 학습, 미리보기, 저장, 목록 조회
- `/patterns/$patternSetId`: 저장된 패턴셋 상세 조회
- `/strategies`: 전략 프로필 생성 및 목록 조회
- `/runs`, `/runs/$runId`: 실행 이력, 결과 차트, 신호, 체결/거절, 거래 애널리틱스 조회
- `/dashboard`: controller 상태, 라이브 루프 상태, 포지션, 최근 이벤트, equity 이력, SSE 연결 상태, 제어 액션(`pause`, `resume`, `reset`, `stop`) 조회
- `/admin`: 브라우저에서 API key 생성, 목록 조회, 폐기

**원스톱 스크립트 (권장):**

```bash
./scripts/run_all.sh            # 백엔드 API + 프론트엔드 개발 서버 동시 실행
./scripts/run_all.sh --backend  # 백엔드만 실행
./scripts/run_all.sh --frontend # 프론트엔드만 실행
```

- 스크립트는 첫 실행 시 `.venv` 생성, Python/npm 의존성 설치, `.env.local` 예제 파일 복사를 자동으로 수행하고 두 서버를 하나의 프로세스로 시작합니다.
- 백엔드 기본 포트는 `8000`, 프론트엔드는 `3000`입니다. `API_PORT`, `FRONTEND_PORT` 환경변수로 변경할 수 있습니다.
- `Ctrl+C`로 모든 서비스를 한 번에 종료합니다.

**수동 두 터미널 방식 (대안):**

```bash
# 터미널 A: 백엔드 API
UV_CACHE_DIR=.uv-cache uv run --python .venv/bin/python --no-sync -m uvicorn trading_system.api.server:create_app --factory --host 0.0.0.0 --port 8000

# 터미널 B: 프론트엔드 개발 서버
cd frontend && npm install && npm run dev
```

브라우저에서 `http://localhost:3000/`를 열면 됩니다.

백엔드 포트를 다르게 쓴다면(예: `9000`), 프론트 화면의 **API Base URL** 입력값을 아래처럼 바꿔 저장하세요.

```text
http://127.0.0.1:9000/api/v1
```

로컬 개발 흐름:

1. 백엔드 API 서버 실행
2. 프론트엔드 개발 서버 실행
3. `/patterns`에서 패턴셋 학습 및 저장
4. `/strategies`에서 전략 프로필 생성
5. `/`에서 백테스트 실행 요청 제출
6. `/runs`, `/runs/<run_id>`에서 결과 및 거래 애널리틱스 확인
7. `/dashboard`에서 연결된 라이브 루프 상태 확인

프론트 클라이언트가 사용하는 API 계약:

- `POST /api/v1/backtests`, `GET /api/v1/backtests/{run_id}`
- `GET /api/v1/analytics/backtests/{run_id}/trades`
- `POST /api/v1/patterns/train`
- `POST /api/v1/patterns`
- `GET /api/v1/patterns`, `GET /api/v1/patterns/{pattern_set_id}`
- `POST /api/v1/strategies`
- `GET /api/v1/strategies`, `GET /api/v1/strategies/{strategy_id}`
- `GET /api/v1/dashboard/status`
- `GET /api/v1/dashboard/positions`
- `GET /api/v1/dashboard/events`
- `GET /api/v1/dashboard/equity`
- `GET /api/v1/dashboard/stream` (SSE, 필요 시 `api_key` 쿼리 파라미터 사용)
- `POST /api/v1/dashboard/control`
- `GET /api/v1/admin/keys`, `POST /api/v1/admin/keys`, `DELETE /api/v1/admin/keys/{key_id}`

프론트 오류 메시지는 다음 경로로 구분해 표시합니다.

- 네트워크 오류: 백엔드 미접속
- 4xx 오류: API 입력/검증 문제
- 5xx 오류: 런타임/서버 내부 문제

대시보드 라우트는 백엔드 API가 활성 라이브 루프와 함께 시작된 경우에만 정상 동작합니다. 그렇지 않으면 대시보드 엔드포인트는 `503`을 반환합니다.

### 5.11 API key management / API Key 관리

### EN

The server supports two complementary ways to enforce API key authentication on all non-admin endpoints. Both can be used simultaneously.

**Method 1 — Static keys via `.env`**

Set one or more comma-separated keys in `.env`:

```
TRADING_SYSTEM_ALLOWED_API_KEYS=my-secret-key,another-key
```

These keys are loaded at startup and are never shown in the Admin UI. Restart the server to add or remove them.

**Method 2 — Dynamic keys via Admin UI**

Open `http://127.0.0.1:3000/admin` in your browser:

1. Enter a name for the key (e.g. `Trading Bot`) and click **Generate Key**.
2. Copy the key from the one-time reveal box — this is the only time the full value is shown in the UI.
3. To revoke a key, click **Revoke** next to it in the Active Keys table.

Dynamic keys are stored in `data/api_keys.json` and take effect immediately without a server restart. The list view exposes only a masked preview, but the underlying file stores the full key value, so file permissions and host-level access still matter.

**Using a key**

Pass the key in the `X-API-Key` request header:

```bash
curl -H "X-API-Key: <your-key>" http://127.0.0.1:8000/api/v1/strategies
```

In the frontend UI, enter the key in the **API Key** field in the settings bar — it is kept in memory only and is not persisted to `localStorage`.

**Authentication rules**

- If neither source has any keys configured, the API is open (no auth required).
- If at least one key exists in either source, all non-admin requests must supply a valid key.
- The `/admin` endpoints are always accessible without a key (bootstrap safety — you need a way to add the first key).
- Rate limiting applies to all endpoints regardless of authentication status.

### KO

서버는 모든 비어드민 엔드포인트에 API Key 인증을 적용하는 두 가지 방법을 지원합니다. 두 방식을 동시에 사용할 수 있습니다.

**방법 1 — `.env`를 통한 정적 키**

`.env`에 쉼표로 구분된 키를 설정합니다:

```
TRADING_SYSTEM_ALLOWED_API_KEYS=my-secret-key,another-key
```

이 키들은 서버 시작 시 로드되며 Admin UI에는 표시되지 않습니다. 추가/삭제 후 서버를 재시작해야 반영됩니다.

**방법 2 — Admin UI를 통한 동적 키**

브라우저에서 `http://127.0.0.1:3000/admin`을 여세요:

1. 키 이름(예: `Trading Bot`)을 입력하고 **Generate Key**를 클릭합니다.
2. 일회성 표시 박스에서 키를 복사하세요 — UI에서 전체 값이 다시 노출되는 시점은 이 생성 직후 한 번뿐입니다.
3. 키를 비활성화하려면 Active Keys 표에서 **Revoke**를 클릭합니다.

동적 키는 `data/api_keys.json`에 저장되며, 서버 재시작 없이 즉시 적용됩니다. 목록 화면에는 마스킹된 preview만 노출되지만 파일 자체에는 전체 키 값이 저장되므로, 파일 권한과 호스트 접근 통제는 여전히 중요합니다.

**키 사용 방법**

요청 헤더 `X-API-Key`에 키를 포함합니다:

```bash
curl -H "X-API-Key: <your-key>" http://127.0.0.1:8000/api/v1/strategies
```

프론트엔드 UI에서는 설정 바의 **API Key** 입력란에 키를 입력합니다 — 메모리에만 유지되며 `localStorage`에는 저장되지 않습니다.

**인증 규칙**

- 어느 쪽에도 키가 설정되지 않으면 API는 인증 없이 열려 있습니다.
- 어느 한 쪽이라도 키가 존재하면, 모든 비어드민 요청은 유효한 키를 제공해야 합니다.
- `/admin` 엔드포인트는 항상 키 없이 접근 가능합니다 (첫 번째 키를 추가하기 위한 부트스트랩 안전장치).
- 인증 여부와 관계없이 모든 엔드포인트에 레이트 리밋이 적용됩니다.

---

## 6) What this system can do now / 현재 시스템으로 할 수 있는 것

### EN

This repository is not a fully managed live-trading product yet. It is a deterministic, test-centered platform that can:

1. Execute end-to-end backtests through CLI and HTTP API.
2. Run live-mode preflight, paper execution, and explicitly gated live execution with configurable polling and heartbeat.
3. Load market data through in-memory (`mock`), CSV (`csv`), and KIS quote-sampling (`kis`) providers.
4. Train and save pattern sets, create reusable strategy profiles, and execute default momentum or pattern-signal strategies.
5. Enforce order risk limits and optional portfolio-level risk controls (`portfolio_risk`) through API/app runtime settings.
6. Simulate fills with policy-based fill ratio, slippage, and commission, or submit real orders through the KIS adapter when explicitly enabled.
7. Update cash/positions, compute equity and drawdown curves, and persist live portfolio state for restart-safe operation.
8. Expose trade analytics and live dashboard APIs for run inspection and operator control.
9. Emit structured logs with sensitive-field redaction and correlation IDs.
10. Provide a browser UI for pattern management, strategy profiles, run review, and dashboard monitoring.

### KO

이 저장소는 아직 완전 관리형 실거래 제품은 아니며, 결정성과 테스트 중심의 플랫폼으로 다음을 수행할 수 있습니다.

1. CLI와 HTTP API를 통한 end-to-end 백테스트 실행.
2. 설정 가능한 polling/heartbeat 기반의 라이브 preflight, 페이퍼 실행, 명시적 가드가 있는 라이브 실행.
3. 인메모리(`mock`), CSV(`csv`), KIS 현재가 샘플링(`kis`) 데이터 공급자 사용.
4. 패턴셋 학습/저장, 재사용 가능한 전략 프로필 생성, 기본 momentum 전략 또는 pattern-signal 전략 실행.
5. API/앱 런타임 설정을 통한 주문 리스크 제한과 선택적 포트폴리오 레벨 리스크(`portfolio_risk`) 적용.
6. 체결 비율/슬리피지/수수료 기반 시뮬레이션 또는 명시적으로 허용된 경우 KIS 어댑터를 통한 실주문 제출.
7. 현금/포지션 갱신, equity/drawdown curve 계산, 라이브 포트폴리오 상태 영속화 및 재기동 복구.
8. 실행 결과 조회와 운영자 제어를 위한 거래 애널리틱스 및 라이브 대시보드 API 제공.
9. 민감정보 마스킹/상관관계 ID를 포함한 구조화 로그 출력.
10. 패턴 관리, 전략 프로필, 실행 결과 검토, 대시보드 모니터링을 위한 브라우저 UI 제공.

---

## 7) Recent updates (compatibility + observability) / 최근 변경 사항 (호환성 + 관측성)

### 7.1 Python compatibility / Python 호환성

### EN

Added `src/trading_system/core/compat.py`:

- `StrEnum`: uses stdlib `enum.StrEnum` on modern Python; falls back to `str + Enum` on older runtimes.
- `UTC`: uses `datetime.UTC` when available; otherwise aliases `timezone.utc`.

This keeps call sites consistent while preventing immediate import failures on Python 3.10 environments.

### KO

`src/trading_system/core/compat.py`를 추가했습니다.

- `StrEnum`: 최신 Python에서는 표준 `enum.StrEnum` 사용, 구버전에서는 `str + Enum` 폴백 사용.
- `UTC`: 가능하면 `datetime.UTC` 사용, 아니면 `timezone.utc` 별칭 사용.

이렇게 호출부를 바꾸지 않으면서 Python 3.10 환경의 import 실패를 방지합니다.

### 7.2 Backtest observability / 백테스트 관측성

### EN

Backtest engine now emits structured lifecycle events:

- `order.created`
- `order.filled`
- `order.rejected` (unfilled)
- `risk.rejected`

This makes signal→risk→execution decisions inspectable, not just final PnL numbers.

### KO

백테스트 엔진이 아래 라이프사이클 이벤트를 구조화 로그로 방출합니다.

- `order.created`
- `order.filled`
- `order.rejected` (미체결)
- `risk.rejected`

이제 최종 손익뿐 아니라 신호→리스크→실행 의사결정 경로를 추적할 수 있습니다.

---

## 8) Required environment variables / 필수 환경변수

### EN

- `TRADING_SYSTEM_ENV`: runtime environment label (`local`, `staging`, `prod`, ...)
- `TRADING_SYSTEM_TIMEZONE`: operator timezone (`Asia/Seoul`, ...)
- `TRADING_SYSTEM_API_KEY`: credential for live adapter preflight
- `TRADING_SYSTEM_ENABLE_LIVE_ORDERS` (optional): set to `true` to allow `--live-execution live` order submission
- `TRADING_SYSTEM_LIVE_BAR_SAMPLES` (optional): KIS live sampling size for one execution cycle (`2` default when `--live-execution live`)
- `TRADING_SYSTEM_KIS_ENV` (optional): KIS environment selector (`prod` default, `mock` available)
- `TRADING_SYSTEM_KIS_APP_KEY` / `TRADING_SYSTEM_KIS_APP_SECRET`: KIS Open API app credentials
- `TRADING_SYSTEM_KIS_CANO` / `TRADING_SYSTEM_KIS_ACNT_PRDT_CD`: KIS account number and product code
- `TRADING_SYSTEM_KIS_BASE_URL` (optional): override KIS REST base URL
- `TRADING_SYSTEM_KIS_PRICE_TR_ID` (optional): override domestic quote TR id for preflight quote checks
- `TRADING_SYSTEM_KIS_BALANCE_TR_ID` (optional): override domestic balance inquiry TR id for reconciliation snapshots
- `TRADING_SYSTEM_KIS_OPEN_ORDERS_TR_ID` (optional): override domestic open-order inquiry TR id for reconciliation pending-order authority
- `TRADING_SYSTEM_KIS_MARKET_DIV` (optional): override quote market division code (`J` default for domestic stock)
- `TRADING_SYSTEM_ALLOWED_API_KEYS`: comma-separated API keys accepted by HTTP middleware (`X-API-Key`)
- `TRADING_SYSTEM_API_KEYS_PATH` (optional): file path for dynamic API key storage managed by `/api/v1/admin/keys` (default: `data/api_keys.json`)
- `TRADING_SYSTEM_CORS_ALLOW_ORIGINS` (optional): comma-separated CORS origins; overrides config file value
- `TRADING_SYSTEM_RATE_LIMIT_MAX_REQUESTS` / `TRADING_SYSTEM_RATE_LIMIT_WINDOW_SECONDS` (optional): simple per-path rate limit
- `TRADING_SYSTEM_CSV_DIR` (optional): CSV directory for `--provider csv` (default: `data/market`)
- `TRADING_SYSTEM_PORTFOLIO_DIR` (optional): Directory where the portfolio book JSON is persisted (default: `data/portfolio`)
- `TRADING_SYSTEM_RUNS_DIR` (optional): Directory for file-based backtest run persistence when `DATABASE_URL` is unset (default: `data/runs`)
- `TRADING_SYSTEM_EQUITY_DIR` (optional): Directory for file-based live equity snapshots when `DATABASE_URL` is unset (default: `data/equity`)
- `DATABASE_URL` (optional): PostgreSQL connection string for Supabase-backed run/equity/session/order persistence. When set, apply `scripts/migrations/001_create_backtest_runs.sql` through `scripts/migrations/007_add_live_order_lifecycle.sql` before starting the API, backtest worker, or live paper mode.
- `TRADING_SYSTEM_LIVE_POLL_INTERVAL` (optional): Seconds to wait between live ticks (default: `10`)
- `TRADING_SYSTEM_HEARTBEAT_INTERVAL` (optional): Seconds between heartbeat logs (default: `60`)
- `TRADING_SYSTEM_RECONCILIATION_INTERVAL` (optional): Seconds between broker balance reconciliation attempts in the live loop (default: `300`)
- `TRADING_SYSTEM_ORDER_POLL_INTERVAL` (optional): Seconds between active live order status polling attempts (default: `30`)
- `TRADING_SYSTEM_ORDER_STALE_AFTER_SECONDS` (optional): Seconds before an unresolved live order is marked stale (default: `120`)
- `TRADING_SYSTEM_WEBHOOK_URL` / `TRADING_SYSTEM_WEBHOOK_EVENTS` / `TRADING_SYSTEM_WEBHOOK_TIMEOUT` (optional): outbound webhook URL, event allowlist, and timeout for fire-and-forget notifications

### KO

- `TRADING_SYSTEM_ENV`: 런타임 환경 라벨 (`local`, `staging`, `prod` 등)
- `TRADING_SYSTEM_TIMEZONE`: 운영 타임존 (`Asia/Seoul` 등)
- `TRADING_SYSTEM_API_KEY`: 라이브 어댑터 프리플라이트용 인증 정보
- `TRADING_SYSTEM_ENABLE_LIVE_ORDERS` (선택): `--live-execution live` 실주문 허용 시 `true`로 설정
- `TRADING_SYSTEM_LIVE_BAR_SAMPLES` (선택): `--live-execution live` 실행 1회당 KIS 시세 샘플 수 (기본값 `2`)
- `TRADING_SYSTEM_KIS_ENV` (선택): 한국투자 Open API 환경 선택 (`prod` 기본값, `mock` 가능)
- `TRADING_SYSTEM_KIS_APP_KEY` / `TRADING_SYSTEM_KIS_APP_SECRET`: 한국투자 Open API 앱 인증정보
- `TRADING_SYSTEM_KIS_CANO` / `TRADING_SYSTEM_KIS_ACNT_PRDT_CD`: 한국투자 계좌번호와 상품코드
- `TRADING_SYSTEM_KIS_BASE_URL` (선택): 한국투자 REST 기본 URL 재정의
- `TRADING_SYSTEM_KIS_PRICE_TR_ID` (선택): 프리플라이트 현재가 조회용 TR ID 재정의
- `TRADING_SYSTEM_KIS_BALANCE_TR_ID` (선택): reconciliation용 국내주식 잔고 조회 TR ID 재정의
- `TRADING_SYSTEM_KIS_OPEN_ORDERS_TR_ID` (선택): reconciliation pending-order 판단용 국내주식 미체결 조회 TR ID 재정의
- `TRADING_SYSTEM_KIS_MARKET_DIV` (선택): 현재가 조회 시장 구분 코드 재정의 (기본값 `J`, 국내주식)
- `TRADING_SYSTEM_ALLOWED_API_KEYS`: HTTP 미들웨어가 허용할 API 키 목록(쉼표 구분, `X-API-Key`)
- `TRADING_SYSTEM_API_KEYS_PATH` (선택): `/api/v1/admin/keys`가 관리하는 동적 API key 저장 파일 경로 (기본값: `data/api_keys.json`)
- `TRADING_SYSTEM_CORS_ALLOW_ORIGINS` (선택): CORS 허용 오리진 목록(쉼표 구분, 설정 파일 값보다 우선)
- `TRADING_SYSTEM_RATE_LIMIT_MAX_REQUESTS` / `TRADING_SYSTEM_RATE_LIMIT_WINDOW_SECONDS` (선택): 경로 단위 단순 요청 제한
- `TRADING_SYSTEM_CSV_DIR` (선택): `--provider csv`용 CSV 디렉터리 (기본값: `data/market`)
- `TRADING_SYSTEM_PORTFOLIO_DIR` (선택): 포트폴리오 상태(JSON)가 영속화되는 디렉터리 (기본값: `data/portfolio`)
- `TRADING_SYSTEM_RUNS_DIR` (선택): `DATABASE_URL`이 없을 때 백테스트 런 메타데이터를 저장하는 디렉터리 (기본값: `data/runs`)
- `TRADING_SYSTEM_EQUITY_DIR` (선택): `DATABASE_URL`이 없을 때 라이브 equity 스냅샷(JSONL)을 저장하는 디렉터리 (기본값: `data/equity`)
- `DATABASE_URL` (선택): Supabase 기반 run/equity/session/order 영속화용 PostgreSQL 연결 문자열. 값을 설정했다면 API, 백테스트 worker, 라이브 페이퍼 모드 시작 전에 `scripts/migrations/001_create_backtest_runs.sql`부터 `scripts/migrations/007_add_live_order_lifecycle.sql`까지 먼저 적용해야 합니다.
- `TRADING_SYSTEM_LIVE_POLL_INTERVAL` (선택): 라이브 루프에서 시세를 받아오는 간격 초 단위 (기본값: `10`)
- `TRADING_SYSTEM_HEARTBEAT_INTERVAL` (선택): 하트비트 로그 기록 간격 (기본값: `60`)
- `TRADING_SYSTEM_RECONCILIATION_INTERVAL` (선택): 라이브 루프의 브로커 잔고 대사 시도 간격 초 단위 (기본값: `300`)
- `TRADING_SYSTEM_ORDER_POLL_INTERVAL` (선택): active live order 상태 polling 간격 초 단위 (기본값: `30`)
- `TRADING_SYSTEM_ORDER_STALE_AFTER_SECONDS` (선택): unresolved live order를 stale로 표시하기까지의 초 단위 시간 (기본값: `120`)
- `TRADING_SYSTEM_WEBHOOK_URL` / `TRADING_SYSTEM_WEBHOOK_EVENTS` / `TRADING_SYSTEM_WEBHOOK_TIMEOUT` (선택): fire-and-forget webhook 알림의 URL, 이벤트 허용 목록, 타임아웃

---

## 9) Configuration schema / 설정 스키마

### EN

`src/trading_system/config/settings.py` provides typed YAML loading + validation:

```python
from trading_system.config import load_settings

settings = load_settings("configs/base.yaml")
```

Required root sections:

- `app`: `environment` (str), `timezone` (str), `mode` (`backtest`|`live`), `reconciliation_interval` (optional int, >= 1)
- `market_data`: `provider` (str), `symbols` (list[str])
- `execution`: `broker` (`paper`|`kis`)
- `risk`: `max_position`, `max_notional`, `max_order_size` (Decimal, > 0)
- `portfolio_risk` (optional): `max_daily_drawdown_pct` (Decimal, > 0 and < 1), `sl_pct`/`tp_pct` (optional Decimal, > 0)
- `backtest`: `starting_cash` (> 0), `fee_bps` (0~1000), `trade_quantity` (> 0)
- `strategy` (optional): `type: pattern_signal` with either `profile_id` or inline `pattern_set_id`, `label_to_side`, `trade_quantity`, and `threshold_overrides`
- `api` (optional): `cors_allow_origins` (list[str], default `[*]`)

All numeric amount/quantity fields are parsed as `Decimal`.

Note:
- `load_settings()` now covers the baseline YAML schema above, including `app.reconciliation_interval`, `portfolio_risk`, and pattern strategy configuration. CLI runs can also use `--config configs/base.yaml` or select a stored profile directly with `--strategy-profile-id`.
- The live loop still uses `TRADING_SYSTEM_RECONCILIATION_INTERVAL` as the runtime env override; YAML provides the typed config baseline.
- Config examples in `configs/base.yaml` and `examples/sample_live_kis.yaml` are active typed fields, not reference-only comments.

### KO

`src/trading_system/config/settings.py`에서 타입 기반 YAML 로딩 및 검증을 제공합니다.

```python
from trading_system.config import load_settings

settings = load_settings("configs/base.yaml")
```

필수 루트 섹션:

- `app`: `environment` (str), `timezone` (str), `mode` (`backtest`|`live`), `reconciliation_interval` (선택 int, 1 이상)
- `market_data`: `provider` (str), `symbols` (list[str])
- `execution`: `broker` (`paper`|`kis`)
- `risk`: `max_position`, `max_notional`, `max_order_size` (Decimal, > 0)
- `portfolio_risk` (선택): `max_daily_drawdown_pct` (Decimal, 0 초과 1 미만), `sl_pct`/`tp_pct` (선택 Decimal, > 0)
- `backtest`: `starting_cash` (> 0), `fee_bps` (0~1000), `trade_quantity` (> 0)
- `strategy` (선택): `type: pattern_signal`과 함께 `profile_id` 또는 inline `pattern_set_id`, `label_to_side`, `trade_quantity`, `threshold_overrides`
- `api` (선택): `cors_allow_origins` (list[str], 기본값 `[*]`)

금액/수량 계열 숫자 필드는 모두 `Decimal`로 파싱됩니다.

참고:
- `load_settings()`는 이제 위 기본 YAML 스키마에 더해 `app.reconciliation_interval`, `portfolio_risk`, pattern strategy 설정까지 타입 검증합니다. CLI는 `--config configs/base.yaml` 또는 `--strategy-profile-id`로 저장된 프로필을 선택할 수 있습니다.
- 라이브 루프 런타임에서는 `TRADING_SYSTEM_RECONCILIATION_INTERVAL` 환경변수가 여전히 우선 override 역할을 하고, YAML은 typed baseline 설정값 역할을 합니다.
- `configs/base.yaml`과 `examples/sample_live_kis.yaml`의 관련 필드는 이제 참고용 주석이 아니라 활성 typed 설정입니다.

---

## 10) Layer responsibilities / 레이어별 책임

### EN

- **app**: CLI parsing, service composition, runtime mode branching
- **data**: provider interfaces and market data loading
- **strategy**: signal generation
- **risk**: order admissibility checks
- **execution**: order model + fill/slippage/fee policies + resilient submit wrapper
- **portfolio**: cash/position updates
- **backtest**: orchestration + result aggregation
- **analytics**: performance metrics
- **core**: logging, redaction, correlation, resilience, compatibility helpers

### KO

- **app**: CLI 파싱, 서비스 조립, 모드 분기
- **data**: 데이터 공급자 인터페이스 및 로딩
- **strategy**: 신호 생성
- **risk**: 주문 허용 여부 검증
- **execution**: 주문 모델 + 체결/슬리피지/수수료 정책 + 복원력 제출 래퍼
- **portfolio**: 현금/포지션 갱신
- **backtest**: 오케스트레이션 + 결과 집계
- **analytics**: 성과 지표 계산
- **core**: 로깅, 마스킹, 상관관계, 복원력, 호환성 유틸

---

## 11) Testing strategy / 테스트 전략

### EN

- Use both unit and integration tests to validate domain rules and orchestration behavior.
- Suggested commands:
  - `uv run --python .venv/bin/python --no-sync pytest -m smoke -q`
  - `uv run --python .venv/bin/python --no-sync pytest -m "not smoke" -q`
- Regression coverage includes:
  - compat behavior (`StrEnum`, `UTC`)
  - backtest event emission (`order.created`, `order.filled`, `risk.rejected`)

### KO

- 단위/통합 테스트를 함께 사용해 도메인 규칙과 오케스트레이션 동작을 검증합니다.
- 권장 명령:
  - `uv run --python .venv/bin/python --no-sync pytest -m smoke -q`
  - `uv run --python .venv/bin/python --no-sync pytest -m "not smoke" -q`
- 회귀 검증 범위:
  - compat 동작 (`StrEnum`, `UTC`)
  - 백테스트 이벤트 방출 (`order.created`, `order.filled`, `risk.rejected`)

---

## 12) Operational cautions / 운영 시 주의사항

### EN

1. **Live order submission is opt-in and KIS-only**: `live` mode defaults to preflight, supports paper simulation with `--live-execution paper`, and only allows real order submission when `--provider kis --broker kis --live-execution live` and `TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true` are set. One execution cycle samples KIS quotes using `TRADING_SYSTEM_LIVE_BAR_SAMPLES` (default `2`).
2. **Secret handling**: inject credentials via environment/secret manager only.
3. **Multi-symbol behavior**: the backtest engine, live loop, and `POST /api/v1/live/preflight` support multiple symbols. The preflight response keeps `quote_summary` for backward compatibility and adds `quote_summaries` plus `symbol_count` for per-symbol readiness detail.
4. **Determinism first**: any backtest logic change should ship with deterministic regression tests.
5. **Dashboard controls**: the live dashboard exposes `pause`, `resume`, `reset`, and `stop`. `GET /api/v1/dashboard/status` still returns controller/preflight context even when no loop is active, while loop-specific endpoints continue to fail with `503` until a loop is attached.
6. **Portfolio-level risk (`portfolio_risk`)**: optional drawdown protection supports `max_daily_drawdown_pct`, `sl_pct`, and `tp_pct`. YAML configs loaded through `config.settings.load_settings()` now parse the same block, so config examples and loader behavior are aligned.
7. **Persistence and reconciliation**: the live loop persists `PortfolioBook` after processed live cycles and reloads it on restart. The KIS adapter queries open-order snapshots first, then broker balance snapshots (cash, positions, average costs), and reconciles them with the local portfolio. Active live orders are stored in a durable lifecycle repository, polled through the broker, exposed on the dashboard, and block new live ticks/reconciliation until resolved or reviewed. YAML configs may now declare `app.reconciliation_interval`, while `TRADING_SYSTEM_RECONCILIATION_INTERVAL` remains the runtime env override for the live loop.
8. **KRX market hours guard**: live order submission (`--live-execution live`) is blocked outside KRX trading hours (weekdays 09:00-15:30 KST). Preflight mode reports `market_closed` as a structured reason but does not block.
9. **Structured preflight readiness**: `/api/v1/live/preflight` returns a structured result with `ready`, `reasons`, `blocking_reasons`, `warnings`, readiness `checks`, per-symbol `symbol_checks`, `next_allowed_actions`, `quote_summary` for the primary symbol, and `quote_summaries`/`symbol_count` for multi-symbol detail instead of a plain message.

### KO

1. **실주문은 명시적 활성화 + KIS 전용**: `live` 모드는 기본 preflight이며, `--live-execution paper`로 페이퍼 실행이 가능하고, `--provider kis --broker kis --live-execution live` + `TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true` 조합일 때만 실주문을 허용합니다. 실행 1회당 KIS 시세 샘플 수는 `TRADING_SYSTEM_LIVE_BAR_SAMPLES`(기본 `2`)로 제어합니다.
2. **시크릿 관리**: 인증정보는 환경변수/시크릿 매니저로만 주입하세요.
3. **다중 심볼 동작 범위**: 백테스트 엔진, 라이브 루프, `POST /api/v1/live/preflight`는 모두 다중 심볼을 지원합니다. 프리플라이트 응답은 하위 호환성을 위해 `quote_summary`를 유지하고, 심볼별 세부 상태를 위해 `quote_summaries`와 `symbol_count`를 추가로 제공합니다.
4. **결정성 우선**: 백테스트 로직 변경 시 결정성 회귀 테스트를 함께 추가하세요.
5. **대시보드 제어**: 라이브 대시보드는 `pause`, `resume`, `reset`, `stop`을 공식 지원합니다. `GET /api/v1/dashboard/status`는 활성 루프가 없어도 controller/preflight 문맥을 반환하고, 루프 의존 엔드포인트만 활성 루프가 없을 때 `503`을 반환합니다.
6. **포트폴리오 레벨 리스크 (`portfolio_risk`)**: `max_daily_drawdown_pct`, `sl_pct`, `tp_pct`를 지원하며, 이제 `config.settings.load_settings()` YAML 로더도 같은 블록을 파싱하므로 설정 예시와 로더 동작이 일치합니다.
7. **영속화와 대사(Reconciliation)**: 라이브 루프는 처리된 라이브 사이클 이후 `PortfolioBook`을 저장하고 재시작 시 다시 로드합니다. KIS 어댑터는 미체결 주문 스냅샷을 먼저 조회한 뒤 브로커 잔고 스냅샷(현금, 포지션, 평균단가)을 조회하여 로컬 포트폴리오와 대사합니다. Active live order는 durable lifecycle 저장소에 기록되고 broker polling/dashboard/cancel flow로 노출되며, unresolved 상태에서는 신규 live tick과 대사를 fail-closed합니다. YAML 설정에서는 `app.reconciliation_interval`을 선언할 수 있고, 런타임에서는 `TRADING_SYSTEM_RECONCILIATION_INTERVAL` 환경변수가 여전히 우선 override 역할을 합니다.
8. **KRX 장시간 가드**: 라이브 실주문(`--live-execution live`)은 KRX 거래 시간(평일 09:00-15:30 KST) 외에는 차단됩니다. Preflight 모드는 `market_closed`를 구조화 사유로 보고하지만 차단하지 않습니다.
9. **구조화된 프리플라이트 결과**: `/api/v1/live/preflight`는 단순 메시지 대신 `ready`, `reasons`, `blocking_reasons`, `warnings`, readiness `checks`, 심볼별 `symbol_checks`, `next_allowed_actions`, 대표 심볼용 `quote_summary`, 그리고 다중 심볼 세부 상태용 `quote_summaries`/`symbol_count` 필드가 포함된 구조화된 결과를 반환합니다.

---

## 13) Suggested next roadmap / 다음 확장 로드맵 제안

### EN

1. ~~**Real-time Live Dashboard:**~~ ✅ Delivered — the frontend dashboard monitors loop state, heartbeat, positions, and events in real-time with `pause`/`resume`/`reset` controls.
2. ~~**Advanced Risk & Analytics:**~~ ✅ Delivered — `portfolio_risk` provides portfolio-level drawdown controls, SL/TP, and the dedicated `/api/v1/analytics/backtests/{run_id}/trades` endpoint exposes trade-level statistics.
3. ~~**Multi-symbol Orchestration:**~~ ✅ Delivered — both backtest and live engines handle multiple symbols under a shared portfolio.
4. ~~**Exchange Reconciliation:**~~ ✅ Delivered — the KIS adapter queries broker balance snapshots (cash, positions, average costs, pending orders) and the live loop reconciles them with the local `PortfolioBook`. Pending symbols are skipped to prevent in-transit corruption. Quote validation, KRX market hours guard, and structured preflight readiness are included.
5. ~~**Phase 6 hardening + parity:**~~ ✅ Delivered — live preflight now supports multi-symbol detail, pending-order detection fails closed when broker signal quality is insufficient, YAML config now covers `app.reconciliation_interval` and `portfolio_risk`, and historical Phase 3/4 task docs are treated as status records rather than the active backlog source.

### KO

1. ~~**실시간 라이브 대시보드:**~~ ✅ 완료 — 프론트엔드 대시보드에서 루프 상태, heartbeat, 포지션, 이벤트를 실시간 모니터링하며 `pause`/`resume`/`reset` 제어가 가능합니다.
2. ~~**고급 리스크 및 분석:**~~ ✅ 완료 — `portfolio_risk`로 포트폴리오 레벨 드로우다운 제한, SL/TP를 제공하며, `/api/v1/analytics/backtests/{run_id}/trades` 전용 엔드포인트에서 트레이드 통계를 조회할 수 있습니다.
3. ~~**다중 심볼 오케스트레이션:**~~ ✅ 완료 — 백테스트와 라이브 엔진 모두 공유 포트폴리오 하에서 다중 심볼을 처리합니다.
4. ~~**거래소 잔고 대사(Reconciliation):**~~ ✅ 완료 — KIS 어댑터가 브로커 잔고 스냅샷(현금, 포지션, 평균단가, 미체결 주문)을 조회하고 라이브 루프가 로컬 `PortfolioBook`과 대사합니다. 미체결 심볼은 건너뛰어 인트랜짓 손상을 방지합니다. 현재가 검증, KRX 장시간 가드, 구조화된 프리플라이트 결과가 포함됩니다.
5. ~~**Phase 6 안정화 + parity:**~~ ✅ 완료 — live preflight는 이제 다중 심볼 세부 상태를 지원하고, pending-order detection은 브로커 신호가 불충분하면 fail-closed로 동작하며, YAML 설정은 `app.reconciliation_interval`과 `portfolio_risk`를 지원합니다. 기존 Phase 3/4 task 문서는 이제 활성 backlog가 아니라 상태 기록으로 해석합니다.

---

## 14) Related docs / 관련 문서

- Architecture overview: `docs/architecture/overview.md` / `docs/architecture/overview.ko.md`
- Workspace analysis: `docs/architecture/workspace-analysis.md` / `docs/architecture/workspace-analysis.ko.md`
- User use cases: `docs/architecture/user-use-cases.md` / `docs/architecture/user-use-cases.ko.md`
- Incident runbook: `docs/runbooks/incident-response.md` / `docs/runbooks/incident-response.ko.md`
- Release gates: `docs/runbooks/release-gate-checklist.md` / `docs/runbooks/release-gate-checklist.ko.md`
- Production deployment: `docs/runbooks/deploy-production.md` / `docs/runbooks/deploy-production.ko.md`
- KRX CSV verification loop note: `docs/runbooks/krx-csv-verification-loop.md` / `docs/runbooks/krx-csv-verification-loop.ko.md`
- KIS domestic live operations: `docs/runbooks/kis-domestic-live-operations.md` / `docs/runbooks/kis-domestic-live-operations.ko.md`

---

## 15) One-line summary / 한 줄 요약

### EN

This repository is a reliable deterministic backtest-and-validation foundation, now standardized on uv-managed Python 3.12 environments with event-level observability.

### KO

이 저장소는 결정적 백테스트/검증 기반을 제공하며, uv 기반 Python 3.12 실행 환경과 이벤트 단위 관측성 강화를 통해 운영 전 단계 품질을 높인 상태입니다.

---

## 16) Deployment guide / 배포 가이드

### EN

This guide covers deploying the backend to Railway, the frontend to Vercel, and the database to Supabase.

#### Step 1 — Supabase (PostgreSQL)

1. Create a project at [supabase.com](https://supabase.com) and copy the **Connection String** (Session mode, port 5432).
2. Apply the schema migrations:
   ```bash
   psql $DATABASE_URL -f scripts/migrations/001_create_backtest_runs.sql
   psql $DATABASE_URL -f scripts/migrations/002_create_equity_snapshots.sql
   psql $DATABASE_URL -f scripts/migrations/003_add_backtest_metadata_and_live_runtime_sessions.sql
   psql $DATABASE_URL -f scripts/migrations/004_add_order_audit_records.sql
   psql $DATABASE_URL -f scripts/migrations/005_add_live_runtime_event_archive.sql
   psql $DATABASE_URL -f scripts/migrations/006_add_backtest_jobs.sql
   psql $DATABASE_URL -f scripts/migrations/007_add_live_order_lifecycle.sql
   ```
3. Store the connection string as `DATABASE_URL` for the next step.

#### Step 2 — Railway (FastAPI backend)

1. Create a new Railway project and connect this GitHub repository.
2. Railway auto-detects `railway.json` and builds with `Dockerfile`.
3. Set the following environment variables in the Railway dashboard:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | Supabase connection string |
   | `TRADING_SYSTEM_ALLOWED_API_KEYS` | Comma-separated API keys for `X-API-Key` header |
   | `TRADING_SYSTEM_CORS_ALLOW_ORIGINS` | Vercel deployment URL (e.g. `https://your-app.vercel.app`) |

4. After deployment, confirm the health check: `GET https://your-backend.railway.app/health` → `{"status": "ok"}`.

#### Step 3 — Vercel (Next.js frontend)

1. Create a new Vercel project and connect this GitHub repository.
2. Set **Root Directory** to `frontend`.
3. Set the following environment variable in the Vercel dashboard:

   | Variable | Value |
   |---|---|
   | `NEXT_PUBLIC_API_BASE_URL` | `https://your-backend.railway.app/api/v1` |

4. Deploy and confirm the frontend loads and can reach the Railway backend.

#### CORS note

`TRADING_SYSTEM_CORS_ALLOW_ORIGINS` must contain the frontend origin (e.g. `https://your-app.vercel.app`). Multiple origins are comma-separated. Trailing slashes are normalized, and wildcard origins such as `https://*.vercel.app` are supported for Vercel preview deployments. The security middleware in `security.py` handles CORS; no additional `CORSMiddleware` is needed.

#### GitHub Actions CI

Push or open a PR to trigger `.github/workflows/ci.yml`. Two jobs run automatically:

- `python-ci` — ruff lint + pytest
- `frontend-ci` — TypeScript check + ESLint + Next.js build

---

### KO

이 가이드는 백엔드를 Railway, 프론트엔드를 Vercel, 데이터베이스를 Supabase에 배포하는 방법을 설명합니다.

#### 1단계 — Supabase (PostgreSQL)

1. [supabase.com](https://supabase.com)에서 프로젝트를 생성하고 **Connection String** (Session mode, 포트 5432)을 복사합니다.
2. 스키마 마이그레이션을 적용합니다:
   ```bash
   psql $DATABASE_URL -f scripts/migrations/001_create_backtest_runs.sql
   psql $DATABASE_URL -f scripts/migrations/002_create_equity_snapshots.sql
   psql $DATABASE_URL -f scripts/migrations/003_add_backtest_metadata_and_live_runtime_sessions.sql
   psql $DATABASE_URL -f scripts/migrations/004_add_order_audit_records.sql
   psql $DATABASE_URL -f scripts/migrations/005_add_live_runtime_event_archive.sql
   psql $DATABASE_URL -f scripts/migrations/006_add_backtest_jobs.sql
   psql $DATABASE_URL -f scripts/migrations/007_add_live_order_lifecycle.sql
   ```
3. 연결 문자열을 다음 단계를 위해 `DATABASE_URL`로 보관합니다.

#### 2단계 — Railway (FastAPI 백엔드)

1. Railway에서 새 프로젝트를 생성하고 이 GitHub 리포지토리를 연결합니다.
2. Railway가 `railway.json`을 자동 감지하고 `Dockerfile`로 빌드합니다.
3. Railway 대시보드에서 다음 환경변수를 설정합니다:

   | 변수 | 값 |
   |---|---|
   | `DATABASE_URL` | Supabase 연결 문자열 |
   | `TRADING_SYSTEM_ALLOWED_API_KEYS` | `X-API-Key` 헤더에 사용할 API 키 목록 (쉼표 구분) |
   | `TRADING_SYSTEM_CORS_ALLOW_ORIGINS` | Vercel 배포 URL (예: `https://your-app.vercel.app`) |

4. 배포 후 헬스체크 확인: `GET https://your-backend.railway.app/health` → `{"status": "ok"}`.

#### 3단계 — Vercel (Next.js 프론트엔드)

1. Vercel에서 새 프로젝트를 생성하고 이 GitHub 리포지토리를 연결합니다.
2. **Root Directory**를 `frontend`로 지정합니다.
3. Vercel 대시보드에서 다음 환경변수를 설정합니다:

   | 변수 | 값 |
   |---|---|
   | `NEXT_PUBLIC_API_BASE_URL` | `https://your-backend.railway.app/api/v1` |

4. 배포 후 프론트엔드가 Railway 백엔드에 정상적으로 요청하는지 확인합니다.

#### CORS 설정

`TRADING_SYSTEM_CORS_ALLOW_ORIGINS`에는 프론트엔드 origin을 입력합니다 (예: `https://your-app.vercel.app`). 여러 오리진은 쉼표로 구분합니다. 끝 슬래시는 자동 정규화되며, Vercel preview 배포용으로 `https://*.vercel.app` 같은 wildcard origin도 지원합니다. CORS는 `security.py`의 보안 미들웨어에서 처리하며, 별도 `CORSMiddleware` 추가는 필요하지 않습니다.

#### GitHub Actions CI

PR을 열거나 push하면 `.github/workflows/ci.yml`이 자동 실행됩니다. 두 job이 순서와 무관하게 병렬 실행됩니다:

- `python-ci` — ruff 린트 + pytest
- `frontend-ci` — TypeScript 검사 + ESLint + Next.js 빌드
