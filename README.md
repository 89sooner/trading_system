# trading_system

Starter scaffold for a modular Python trading system.

## Goals

- Separate market data, strategy, risk, execution, portfolio, backtest, and analytics concerns.
- Keep domain logic testable without live infrastructure.
- Make it easy to grow from local research to a more production-like service layout.

## Repository layout

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

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

## Run commands

### One-command local run

If you want to run immediately without manually creating a venv or exporting variables:

```bash
./scripts/run_engine.sh backtest
./scripts/run_engine.sh live-preflight
```

- The script auto-creates `.venv` (if missing), installs dependencies, and runs the CLI.
- `live-preflight` uses `TRADING_SYSTEM_API_KEY` from your environment when present; otherwise it injects a local dummy key for preflight only.

This repository currently provides a clean package skeleton, a small risk-rule example, a deterministic single-symbol backtest loop, a chart-pattern learning and matching scaffold, and repository-level skills for planning, implementation, review, and documentation work.

- Fast smoke set: `pytest -m smoke -q`
- Extended set: `pytest -m "not smoke" -q`

### Backtest mode

```bash
PYTHONPATH=src TRADING_SYSTEM_ENV=local TRADING_SYSTEM_TIMEZONE=Asia/Seoul \
python -m trading_system.app.main --mode backtest --symbols BTCUSDT
```

### Backtest mode (KRX CSV example)

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

### Live preflight mode (no order submission)

```bash
PYTHONPATH=src TRADING_SYSTEM_ENV=local TRADING_SYSTEM_TIMEZONE=Asia/Seoul \
TRADING_SYSTEM_API_KEY=dummy-key \
python -m trading_system.app.main --mode live --symbols BTCUSDT
```

The built-in smoke backtest module is still available and routes through the app layer:

```bash
PYTHONPATH=src python -m trading_system.backtest.example
```

## Required environment variables

- `TRADING_SYSTEM_ENV`: logical runtime environment name (for example `local`, `staging`, `prod`).
- `TRADING_SYSTEM_TIMEZONE`: operator timezone used for runtime context (for example `Asia/Seoul`).
- `TRADING_SYSTEM_API_KEY`: live adapter credential injected from environment/secret manager only.
- `TRADING_SYSTEM_CSV_DIR` (optional): directory for CSV backtest files when `--provider csv` is used (default: `data/market`).

## Configuration schema

`src/trading_system/config/settings.py` provides a YAML loader with validation:

```python
from trading_system.config import load_settings

settings = load_settings("configs/base.yaml")
```

Required top-level sections:

- `app`: `environment` (str), `timezone` (str), `mode` (`backtest`|`live`)
- `market_data`: `provider` (str), `symbols` (list[str])
- `risk`: `max_position`, `max_notional`, `max_order_size` (Decimal, > 0)
- `backtest`: `starting_cash` (> 0), `fee_bps` (0~1000), `trade_quantity` (> 0)

All amount/quantity/fee fields are parsed as `Decimal`. Validation errors return human-friendly messages for missing keys, invalid types, and out-of-range values.

## Analysis docs

- Architecture overview: `docs/architecture/overview.md`
- Current workspace analysis: `docs/architecture/workspace-analysis.md`
- Incident runbook: `docs/runbooks/incident-response.md`
- Release gates: `docs/runbooks/release-gate-checklist.md`
- KRX CSV verification loop note: `docs/runbooks/krx-csv-verification-loop.md`

## Operations baseline

- a built-in stateful `MomentumStrategy`
- close-price immediate fills
- fee-aware cash updates
- a printed equity curve and return summary

## Pattern-learning scaffold

The repository now includes a minimal chart-pattern pipeline for:

- storing labeled bar windows as training examples
- learning per-label pattern prototypes from those examples
- scoring the current bar window against learned patterns
- emitting alerts or converting matches into strategy signals

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

2. **라이브 프리플라이트(preflight) 실행**
   - `--mode live`는 실제 주문을 보내지 않고 운영 필수 입력(예: API 키)만 사전 검증합니다.

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

- **app**: CLI 입력 처리, 서비스 조립, 모드 분기(backtest/live preflight)
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
   - 현재 `live`는 preflight 전용이며 실제 주문 제출은 구현되어 있지 않습니다.

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
