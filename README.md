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

### 5.5 Live preflight mode (no order submission) / 라이브 프리플라이트 모드 (실주문 없음)

```bash
PYTHONPATH=src TRADING_SYSTEM_ENV=local TRADING_SYSTEM_TIMEZONE=Asia/Seoul \
TRADING_SYSTEM_API_KEY=dummy-key \
python -m trading_system.app.main --mode live --symbols BTCUSDT
```

### 5.6 Built-in backtest example / 내장 백테스트 예시

```bash
PYTHONPATH=src python -m trading_system.backtest.example
```

---

## 6) What this system can do now / 현재 시스템으로 할 수 있는 것

### EN
This repository is not a fully live-trading product yet. It is a deterministic, test-centered platform that can:

1. Execute end-to-end backtests through CLI.
2. Run live-mode preflight checks without submitting real orders.
3. Load market data via in-memory provider (`mock`) or CSV provider (`csv`).
4. Enforce risk limits (`max_position`, `max_notional`, `max_order_size`).
5. Simulate fills via fill ratio, slippage (bps), and commission (bps).
6. Update cash/positions and compute equity curve + cumulative return.
7. Train/match chart patterns and convert matches into strategy signals.
8. Emit structured logs with sensitive-field redaction and correlation IDs.

### KO
이 저장소는 아직 “완전한 실주문 시스템”은 아니며, 결정성과 테스트 중심의 플랫폼으로 다음을 수행할 수 있습니다.

1. CLI 기반 end-to-end 백테스트 실행.
2. 실주문 없이 라이브 프리플라이트 검증 수행.
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
- `TRADING_SYSTEM_CSV_DIR` (optional): CSV directory for `--provider csv` (default: `data/market`)

### KO
- `TRADING_SYSTEM_ENV`: 런타임 환경 라벨 (`local`, `staging`, `prod` 등)
- `TRADING_SYSTEM_TIMEZONE`: 운영 타임존 (`Asia/Seoul` 등)
- `TRADING_SYSTEM_API_KEY`: 라이브 어댑터 프리플라이트용 인증 정보
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
1. **No real live order submission yet**: `live` mode is currently preflight-only.
2. **Secret handling**: inject credentials via environment/secret manager only.
3. **Current scaffold limitation**: app composition currently focuses on a single-symbol runtime path for simplicity/safety.
4. **Determinism first**: any backtest logic change should ship with deterministic regression tests.

### KO
1. **실주문 미지원**: 현재 `live` 모드는 preflight 전용입니다.
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
