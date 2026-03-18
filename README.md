# trading_system / 트레이딩 시스템

> **Language policy / 언어 정책**
>
> - **EN:** This README is maintained in both English and Korean with the same level of detail. Any future README updates must be reflected in **both languages**.
> - **KO:** 이 README는 영어/한국어를 **동일한 수준의 상세도**로 유지합니다. 앞으로 README를 수정할 때는 **두 언어 모두** 반드시 함께 업데이트해야 합니다.

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
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

### KO
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

---

## 5) Run commands / 실행 명령

### 5.1 One-command local run / 원커맨드 로컬 실행

### EN
```bash
./scripts/run_engine.sh backtest
./scripts/run_engine.sh live-preflight
```

- The script auto-creates `.venv` (if missing), installs dependencies, and runs the CLI.
- `live-preflight` uses `TRADING_SYSTEM_API_KEY` from your environment when available; otherwise it injects a local dummy key for preflight only.

### KO
```bash
./scripts/run_engine.sh backtest
./scripts/run_engine.sh live-preflight
```

- 스크립트는 `.venv`가 없으면 자동 생성하고, 의존성을 설치한 뒤 CLI를 실행합니다.
- `live-preflight`는 환경변수 `TRADING_SYSTEM_API_KEY`가 있으면 사용하고, 없으면 프리플라이트 전용 더미 키를 주입합니다.

### 5.2 Test subsets / 테스트 세트

### EN
- Fast smoke set: `pytest -m smoke -q`
- Extended set: `pytest -m "not smoke" -q`

### KO
- 빠른 스모크 세트: `pytest -m smoke -q`
- 확장 세트: `pytest -m "not smoke" -q`

### 5.3 Backtest mode / 백테스트 모드

```bash
PYTHONPATH=src TRADING_SYSTEM_ENV=local TRADING_SYSTEM_TIMEZONE=Asia/Seoul \
python -m trading_system.app.main --mode backtest --symbols BTCUSDT
```

### 5.4 Backtest mode (KRX CSV example) / 백테스트 모드 (KRX CSV 예시)

```bash
mkdir -p data/market
cat > data/market/005930.csv <<'CSV'
timestamp,open,high,low,close,volume
2024-01-02T00:00:00+00:00,70000,70500,69900,70400,1000
2024-01-03T00:00:00+00:00,70400,71000,70300,70900,1200
CSV

PYTHONPATH=src TRADING_SYSTEM_ENV=local TRADING_SYSTEM_TIMEZONE=Asia/Seoul \
TRADING_SYSTEM_CSV_DIR=data/market \
python -m trading_system.app.main --mode backtest --provider csv --symbols 005930 --trade-quantity 1
```

### 5.5 Live preflight mode (default, no order submission) / 라이브 프리플라이트 모드 (기본값, 실주문 없음)

```bash
PYTHONPATH=src TRADING_SYSTEM_ENV=local TRADING_SYSTEM_TIMEZONE=Asia/Seoul \
TRADING_SYSTEM_API_KEY=dummy-key \
python -m trading_system.app.main --mode live --symbols BTCUSDT
```

### 5.6 Live paper mode (explicit opt-in) / 라이브 페이퍼 모드 (명시적 활성화)

```bash
PYTHONPATH=src TRADING_SYSTEM_ENV=local TRADING_SYSTEM_TIMEZONE=Asia/Seoul \
TRADING_SYSTEM_API_KEY=dummy-key \
python -m trading_system.app.main --mode live --symbols BTCUSDT --live-execution paper
```

### 5.7 Built-in backtest example / 내장 백테스트 예시

```bash
PYTHONPATH=src python -m trading_system.backtest.example
```

### 5.8 HTTP API mode / HTTP API 모드

### EN
Run API server:

```bash
PYTHONPATH=src uvicorn trading_system.api.server:create_app --factory --host 0.0.0.0 --port 8000
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
      {"timestamp": "2024-01-01T00:00:00Z", "equity": "10000"},
      {"timestamp": "2024-01-02T00:00:00Z", "equity": "10125"}
    ],
    "drawdown_curve": [
      {"timestamp": "2024-01-01T00:00:00Z", "drawdown": "0"},
      {"timestamp": "2024-01-02T00:00:00Z", "drawdown": "0"}
    ],
    "orders": [
      {
        "event": "order.filled",
        "payload": {"symbol": "BTCUSDT", "filled_quantity": "0.1", "status": "filled"}
      }
    ],
    "risk_rejections": [
      {
        "event": "risk.rejected",
        "payload": {"symbol": "BTCUSDT", "requested_quantity": "0.5"}
      }
    ]
  }
}
```

### KO
API 서버 실행:

```bash
PYTHONPATH=src uvicorn trading_system.api.server:create_app --factory --host 0.0.0.0 --port 8000
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
      {"timestamp": "2024-01-01T00:00:00Z", "equity": "10000"},
      {"timestamp": "2024-01-02T00:00:00Z", "equity": "10125"}
    ],
    "drawdown_curve": [
      {"timestamp": "2024-01-01T00:00:00Z", "drawdown": "0"},
      {"timestamp": "2024-01-02T00:00:00Z", "drawdown": "0"}
    ],
    "orders": [
      {
        "event": "order.filled",
        "payload": {"symbol": "BTCUSDT", "filled_quantity": "0.1", "status": "filled"}
      }
    ],
    "risk_rejections": [
      {
        "event": "risk.rejected",
        "payload": {"symbol": "BTCUSDT", "requested_quantity": "0.5"}
      }
    ]
  }
}
```

### 5.9 Frontend + backend local development / 프론트엔드 + 백엔드 로컬 개발

### EN
The repository now includes a minimal static frontend under `frontend/` with three pages:

- `frontend/index.html`: backtest run form (symbol/risk/fee inputs)
- `frontend/runs.html`: run list and status refresh
- `frontend/run.html?run_id=<id>`: result details with equity/drawdown time-series charts and fill/rejection event table

Run backend and frontend together in two terminals:

```bash
# Terminal A: backend API
PYTHONPATH=src uvicorn trading_system.api.server:create_app --factory --host 0.0.0.0 --port 8000

# Terminal B: static frontend
python -m http.server 5173 -d frontend
```

Open `http://127.0.0.1:5173/index.html`.

Local development flow:

1. Start backend API server.
2. Start frontend static server.
3. Submit a run from `index.html`.
4. Check run status in `runs.html`.
5. Inspect charts/events in `run.html?run_id=<id>`.

API endpoint contract used by frontend client:

- `POST /api/v1/backtests` → create run
- `GET /api/v1/backtests/{run_id}` → fetch run status/result

Frontend error handling is separated by path:

- Network failure: backend not reachable
- 4xx failure: validation/input issue from API
- 5xx failure: runtime/internal server issue

### KO
저장소에는 `frontend/` 경로에 최소 정적 프론트엔드가 포함되어 있으며, 다음 3개 페이지를 제공합니다.

- `frontend/index.html`: 백테스트 실행 폼 (심볼/리스크/수수료 입력)
- `frontend/runs.html`: 실행 목록 및 상태 갱신
- `frontend/run.html?run_id=<id>`: Equity/Drawdown 시계열 차트 + 체결/거절 이벤트 테이블 상세

백엔드와 프론트를 각각 다른 터미널에서 실행하세요:

```bash
# 터미널 A: 백엔드 API
PYTHONPATH=src uvicorn trading_system.api.server:create_app --factory --host 0.0.0.0 --port 8000

# 터미널 B: 정적 프론트엔드 서버
python -m http.server 5173 -d frontend
```

브라우저에서 `http://127.0.0.1:5173/index.html`를 열면 됩니다.

로컬 개발 흐름:

1. 백엔드 API 서버 실행
2. 프론트 정적 서버 실행
3. `index.html`에서 실행 요청 제출
4. `runs.html`에서 상태 확인
5. `run.html?run_id=<id>`에서 차트/이벤트 상세 확인

프론트 클라이언트가 사용하는 API 계약:

- `POST /api/v1/backtests` → 실행 생성
- `GET /api/v1/backtests/{run_id}` → 실행 상태/결과 조회

프론트 오류 메시지는 다음 경로로 구분해 표시합니다.

- 네트워크 오류: 백엔드 미접속
- 4xx 오류: API 입력/검증 문제
- 5xx 오류: 런타임/서버 내부 문제

---

## 6) What this system can do now / 현재 시스템으로 할 수 있는 것

### EN
This repository is not a fully live-trading product yet. It is a deterministic, test-centered platform that can:

1. Execute end-to-end backtests through CLI.
2. Run live-mode preflight checks (default) or an explicit paper execution loop (`--live-execution paper`) without submitting real orders.
3. Load market data via in-memory provider (`mock`) or CSV provider (`csv`).
4. Enforce risk limits (`max_position`, `max_notional`, `max_order_size`).
5. Simulate fills via fill ratio, slippage (bps), and commission (bps).
6. Update cash/positions and compute equity curve + cumulative return.
7. Train/match chart patterns and convert matches into strategy signals.
8. Emit structured logs with sensitive-field redaction and correlation IDs.

### KO
이 저장소는 아직 “완전한 실주문 시스템”은 아니며, 결정성과 테스트 중심의 플랫폼으로 다음을 수행할 수 있습니다.

1. CLI 기반 end-to-end 백테스트 실행.
2. 실주문 없이 라이브 프리플라이트(기본) 또는 명시적 페이퍼 실행 루프(`--live-execution paper`) 수행.
3. 인메모리(`mock`) 또는 CSV(`csv`) 데이터 공급자 사용.
4. 리스크 제한(`max_position`, `max_notional`, `max_order_size`) 적용.
5. 체결 비율/슬리피지(bps)/수수료(bps) 기반 체결 시뮬레이션.
6. 현금/포지션 갱신 및 equity curve + 누적수익률 계산.
7. 차트 패턴 학습/매칭 및 전략 신호 변환.
8. 민감정보 마스킹/상관관계 ID를 포함한 구조화 로그 출력.

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
- `TRADING_SYSTEM_ALLOWED_API_KEYS`: comma-separated API keys accepted by HTTP middleware (`X-API-Key`)
- `TRADING_SYSTEM_CORS_ALLOW_ORIGINS` (optional): comma-separated CORS origins; overrides config file value
- `TRADING_SYSTEM_RATE_LIMIT_MAX_REQUESTS` / `TRADING_SYSTEM_RATE_LIMIT_WINDOW_SECONDS` (optional): simple per-path rate limit
- `TRADING_SYSTEM_CSV_DIR` (optional): CSV directory for `--provider csv` (default: `data/market`)

### KO
- `TRADING_SYSTEM_ENV`: 런타임 환경 라벨 (`local`, `staging`, `prod` 등)
- `TRADING_SYSTEM_TIMEZONE`: 운영 타임존 (`Asia/Seoul` 등)
- `TRADING_SYSTEM_API_KEY`: 라이브 어댑터 프리플라이트용 인증 정보
- `TRADING_SYSTEM_ALLOWED_API_KEYS`: HTTP 미들웨어가 허용할 API 키 목록(쉼표 구분, `X-API-Key`)
- `TRADING_SYSTEM_CORS_ALLOW_ORIGINS` (선택): CORS 허용 오리진 목록(쉼표 구분, 설정 파일 값보다 우선)
- `TRADING_SYSTEM_RATE_LIMIT_MAX_REQUESTS` / `TRADING_SYSTEM_RATE_LIMIT_WINDOW_SECONDS` (선택): 경로 단위 단순 요청 제한
- `TRADING_SYSTEM_CSV_DIR` (선택): `--provider csv`용 CSV 디렉터리 (기본값: `data/market`)

---

## 9) Configuration schema / 설정 스키마

### EN
`src/trading_system/config/settings.py` provides typed YAML loading + validation:

```python
from trading_system.config import load_settings

settings = load_settings("configs/base.yaml")
```

Required root sections:
- `app`: `environment` (str), `timezone` (str), `mode` (`backtest`|`live`)
- `market_data`: `provider` (str), `symbols` (list[str])
- `risk`: `max_position`, `max_notional`, `max_order_size` (Decimal, > 0)
- `backtest`: `starting_cash` (> 0), `fee_bps` (0~1000), `trade_quantity` (> 0)
- `api` (optional): `cors_allow_origins` (list[str], default `[*]`)

All numeric amount/quantity fields are parsed as `Decimal`.

### KO
`src/trading_system/config/settings.py`에서 타입 기반 YAML 로딩 및 검증을 제공합니다.

```python
from trading_system.config import load_settings

settings = load_settings("configs/base.yaml")
```

필수 루트 섹션:
- `app`: `environment` (str), `timezone` (str), `mode` (`backtest`|`live`)
- `market_data`: `provider` (str), `symbols` (list[str])
- `risk`: `max_position`, `max_notional`, `max_order_size` (Decimal, > 0)
- `backtest`: `starting_cash` (> 0), `fee_bps` (0~1000), `trade_quantity` (> 0)
- `api` (선택): `cors_allow_origins` (list[str], 기본값 `[*]`)

금액/수량 계열 숫자 필드는 모두 `Decimal`로 파싱됩니다.

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
  - `pytest -m smoke -q`
  - `pytest -m "not smoke" -q`
- Regression coverage includes:
  - compat behavior (`StrEnum`, `UTC`)
  - backtest event emission (`order.created`, `order.filled`, `risk.rejected`)

### KO
- 단위/통합 테스트를 함께 사용해 도메인 규칙과 오케스트레이션 동작을 검증합니다.
- 권장 명령:
  - `pytest -m smoke -q`
  - `pytest -m "not smoke" -q`
- 회귀 검증 범위:
  - compat 동작 (`StrEnum`, `UTC`)
  - 백테스트 이벤트 방출 (`order.created`, `order.filled`, `risk.rejected`)

---

## 12) Operational cautions / 운영 시 주의사항

### EN
1. **No real live order submission yet**: `live` mode defaults to preflight, and supports paper simulation only when `--live-execution paper` is set.
2. **Secret handling**: inject credentials via environment/secret manager only.
3. **Current scaffold limitation**: app composition currently focuses on a single-symbol runtime path for simplicity/safety.
4. **Determinism first**: any backtest logic change should ship with deterministic regression tests.

### KO
1. **실주문 미지원**: 현재 `live` 모드는 기본 preflight이며, `--live-execution paper` 지정 시 페이퍼 시뮬레이션만 지원합니다.
2. **시크릿 관리**: 인증정보는 환경변수/시크릿 매니저로만 주입하세요.
3. **현재 스캐폴드 제약**: 단순성과 안전성을 위해 앱 조립 경로는 단일 심볼 중심입니다.
4. **결정성 우선**: 백테스트 로직 변경 시 결정성 회귀 테스트를 함께 추가하세요.

---

## 13) Suggested next roadmap / 다음 확장 로드맵 제안

### EN
1. Add real market-data adapter and broker adapter behind existing interfaces.
2. Introduce paper/live runtime loop with heartbeat and explicit state transitions.
3. Add persistence/recovery for restart-safe operation.
4. Expand risk and analytics (portfolio-level controls, drawdown/trade stats).

### KO
1. 기존 인터페이스 뒤에 실데이터/실브로커 어댑터를 추가합니다.
2. heartbeat 및 명시적 상태전이를 갖춘 paper/live 런타임 루프를 도입합니다.
3. 재시작 안전성을 위한 영속화/복구 체계를 추가합니다.
4. 포트폴리오 레벨 리스크 및 드로우다운/트레이드 통계 등 분석 지표를 확장합니다.

---

## 14) Related docs / 관련 문서

- Architecture overview: `docs/architecture/overview.md`
- Workspace analysis: `docs/architecture/workspace-analysis.md`
- Incident runbook: `docs/runbooks/incident-response.md`
- Release gates: `docs/runbooks/release-gate-checklist.md`
- KRX CSV verification loop note: `docs/runbooks/krx-csv-verification-loop.md`

---

## 15) One-line summary / 한 줄 요약

### EN
This repository is a reliable deterministic backtest-and-validation foundation, now strengthened with Python 3.10+ compatibility and event-level observability.

### KO
이 저장소는 결정적 백테스트/검증 기반을 제공하며, Python 3.10+ 호환성과 이벤트 단위 관측성 강화를 통해 운영 전 단계 품질을 높인 상태입니다.
Run the example matcher with:

```bash
PYTHONPATH=src python -m trading_system.patterns.example
```

---

## 한국어 상세 가이드

이 섹션은 현재 시스템이 **실제로 할 수 있는 일**, 최근 변경 사항(호환성/관측성 강화), 운영 시 주의사항을 한국어로 정리한 문서입니다.

### 1) 이 시스템으로 할 수 있는 것

현재 저장소는 “실주문 브로커 연동 완성본”이 아니라, 아래 기능을 갖춘 **결정적(deterministic) 트레이딩 백테스트/검증 플랫폼**입니다.

1. **CLI 기반 백테스트 실행**
   - 전략 신호 생성 → 주문 변환 → 리스크 검증 → 체결 시뮬레이션 → 포트폴리오 반영 → 성과 계산을 일괄 수행합니다.

2. **라이브 실행(preflight/paper) 지원**
   - `--mode live`는 기본적으로 preflight를 수행하며, `--live-execution paper`를 지정하면 실주문 없이 페이퍼 실행 루프를 수행합니다.

3. **시장 데이터 공급 선택**
   - `mock` 인메모리 데이터(테스트/스모크용)
   - `csv` 데이터(심볼별 CSV 파일 로딩, KRX 심볼 포함)

4. **리스크 가드레일 적용**
   - `max_position`, `max_notional`, `max_order_size` 제약으로 비정상 주문을 차단합니다.

5. **체결 정책 시뮬레이션**
   - 부분 체결/미체결(fill ratio)
   - 슬리피지(BPS)
   - 수수료(BPS)

6. **포트폴리오/성과 계산**
   - 현금 및 포지션 갱신, 수수료 반영
   - equity curve 및 누적 수익률 산출

7. **패턴 학습/매칭 파이프라인**
   - 라벨링된 바 윈도우 학습
   - 현재 윈도우와 유사도 매칭
   - 알림 생성 및 전략 신호 변환

8. **구조화 로깅/복원력 공통 유틸**
   - JSON/key-value 로그
   - 민감 정보 마스킹
   - 상관관계 ID(correlation id)
   - 재시도/타임아웃/서킷브레이커

### 2) 최근 핵심 변경 사항 (호환성 + 관측성)

#### A. Python 3.10+ 호환성 강화

`src/trading_system/core/compat.py`를 추가하여 다음을 제공하도록 개선했습니다.

- `StrEnum`:
  - Python 3.11+에서는 표준 `enum.StrEnum`
  - 하위 버전에서는 `str + Enum` 폴백
- `UTC`:
  - Python 3.11+에서는 `datetime.UTC`
  - 하위 버전에서는 `timezone.utc` 폴백

이로써 실행 환경이 3.10인 경우에도 import 단계에서 즉시 실패하지 않고, 동일한 호출부를 유지하면서 동작할 수 있습니다.

#### B. 백테스트 관측성(Observability) 강화

백테스트 엔진에서 구조화 이벤트를 실제 방출하도록 개선했습니다.

- `order.created`: 주문 생성
- `order.filled`: 체결 성공
- `order.rejected`: 주문은 생성됐으나 미체결
- `risk.rejected`: 리스크 룰로 주문 차단

이벤트가 추가되면서, 단순히 “최종 수익률”만 보는 것이 아니라 **중간 의사결정 경로(신호→리스크→체결)를 운영/테스트에서 추적**할 수 있습니다.

### 3) 아키텍처 레이어별 역할 요약

- **app**: CLI 입력 처리, 서비스 조립, 모드 분기(backtest/live preflight/paper)
- **data**: 데이터 공급자 인터페이스 및 구현(mock/csv)
- **strategy**: 전략 신호 생성
- **risk**: 주문 가능 여부 검증
- **execution**: 주문 모델, 체결 정책, 복원력 래퍼 브로커
- **portfolio**: 체결 결과 반영(현금/포지션)
- **backtest**: 오케스트레이션 및 성과 집계
- **analytics**: 성과 지표 계산(예: cumulative return)
- **core**: 로깅, redaction, correlation, resilience, compat 유틸

### 4) 설정 방법 요약

- YAML 기반 설정은 `src/trading_system/config/settings.py`에서 파싱/검증합니다.
- 주요 섹션
  - `app`: 실행 환경/타임존/모드
  - `market_data`: 공급자/심볼 목록
  - `risk`: 포지션/노셔널/주문량 제한
  - `backtest`: 시작자금/수수료/거래수량
- 수치형 값은 `Decimal`로 파싱되어 금액 계산 오차를 줄입니다.

### 5) 테스트 및 검증 전략

- 단위 테스트 + 통합 테스트를 통해 전략/리스크/실행/오케스트레이션을 검증합니다.
- 대표 실행
  - `pytest -m smoke -q`
  - `pytest -m "not smoke" -q`
- 최근 추가된 회귀 검증
  - compat 모듈(`StrEnum`, `UTC`) 동작 확인
  - 백테스트 이벤트 방출(`order.created`, `order.filled`, `risk.rejected`) 확인

### 6) 운영 시 주의사항

1. **실주문 미지원**
   - 현재 `live`는 기본 preflight이며, `--live-execution paper`로 페이퍼 실행만 가능합니다(실주문 제출 미구현).

2. **시크릿 관리**
   - API 키는 반드시 환경변수/시크릿 매니저로 주입하고 코드/로그에 직접 남기지 마세요.

3. **단일 심볼 제약(앱 스캐폴드)**
   - 현재 app 조립 경로는 안전성과 단순성을 위해 단일 심볼 중심입니다.

4. **결정성 유지**
   - 백테스트 로직 변경 시 결정성이 유지되도록 테스트를 함께 보강해야 합니다.

### 7) 앞으로 확장하면 좋은 우선순위

1. 실데이터/실브로커 어댑터 추가(기존 프로토콜 뒤에 연결)
2. 라이브 루프(heartbeat, 상태전이, 재기동 복구) 구현
3. 주문/포지션 영속화 및 리플레이 체계
4. 고급 리스크(포트폴리오 레벨) 및 고급 지표(드로우다운/트레이드 통계) 확장

### 8) 한 줄 요약

이 저장소는 현재 **신뢰 가능한 백테스트/검증 기반을 제공하는 트레이딩 시스템 골격**이며,
호환성(3.10+)과 관측성(구조화 이벤트) 강화로 실제 서비스 전개 전 단계의 품질 기준을 충족하도록 발전하고 있습니다.
