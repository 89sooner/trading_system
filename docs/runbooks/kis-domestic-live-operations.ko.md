# KIS 국내주식 라이브 운영 런북

## 사전 조건

1. KIS Open API 인증정보 환경변수 설정:
   - `TRADING_SYSTEM_KIS_APP_KEY` / `TRADING_SYSTEM_KIS_APP_SECRET`
   - `TRADING_SYSTEM_KIS_CANO` / `TRADING_SYSTEM_KIS_ACNT_PRDT_CD`
2. 선택적 재정의: `TRADING_SYSTEM_KIS_ENV`, `TRADING_SYSTEM_KIS_BASE_URL`, `TRADING_SYSTEM_KIS_MARKET_DIV`

## 워크플로우: CSV 백테스트 -> KIS 프리플라이트 -> 가드된 라이브

### 1단계: CSV 백테스트

```bash
TRADING_SYSTEM_CSV_DIR=data/market \
uv run -m trading_system.app.main --mode backtest --provider csv --broker paper --symbols 005930
```

백테스트가 완료되고 수익률/드로우다운 곡선이 생성되는지 확인합니다.

### 2단계: KIS 프리플라이트

```bash
TRADING_SYSTEM_KIS_APP_KEY=your-key \
TRADING_SYSTEM_KIS_APP_SECRET=your-secret \
TRADING_SYSTEM_KIS_CANO=12345678 \
TRADING_SYSTEM_KIS_ACNT_PRDT_CD=01 \
uv run -m trading_system.app.main --mode live --provider kis --broker kis --symbols 005930
```

기본 `--live-execution preflight`는 실시간 KIS 현재가를 조회하고 구조화된 준비 상태 결과를 반환합니다:
- `ready: true/false`
- `reasons`: 이슈 목록 (예: `market_closed`, `zero_volume`, `quote_error`)
- `quote_summary`: 종목코드, 가격, 거래량

### 3단계: 가드된 라이브 실행

```bash
TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true \
TRADING_SYSTEM_LIVE_BAR_SAMPLES=2 \
TRADING_SYSTEM_KIS_APP_KEY=your-key \
TRADING_SYSTEM_KIS_APP_SECRET=your-secret \
TRADING_SYSTEM_KIS_CANO=12345678 \
TRADING_SYSTEM_KIS_ACNT_PRDT_CD=01 \
uv run -m trading_system.app.main --mode live --provider kis --broker kis --symbols 005930 --live-execution live
```

**적용되는 가드:**
- `TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true` 설정 필수
- KRX 장시간만 허용 (평일 09:00-15:30 KST)
- 현재가 검증 (가격 > 0, 거래량 >= 0)

## 대사(Reconciliation)

라이브 루프는 `TRADING_SYSTEM_RECONCILIATION_INTERVAL`초(기본값: 300)마다 로컬 `PortfolioBook`을 KIS 브로커 잔고와 대사합니다.

**동작 방식:**
- 현금 및 포지션 차이를 브로커 스냅샷에 맞게 조정
- 평균단가를 브로커에서 동기화
- 미체결 주문이 있는 심볼은 건너뜀 (인트랜짓 보호)
- 미체결 주문 존재 시 현금도 동결
- 잔고 조회 실패 시 대사 전체 건너뜀 (fail-closed)

**구조화 로그 이벤트:**
- `portfolio.reconciliation.cash_adjusted` — 현금 차이 감지 및 보정
- `portfolio.reconciliation.position_adjusted` — 포지션 차이 감지 및 보정
- `portfolio.reconciliation.average_cost_adjusted` — 브로커에서 평균단가 동기화
- `portfolio.reconciliation.symbol_skipped` — 미체결 주문으로 심볼 건너뜀
- `portfolio.reconciliation.cash_frozen` — 미체결 심볼로 인한 현금 동결
- `portfolio.reconciliation.skipped` — 전체 대사 건너뜀 (스냅샷 불가)

## 대시보드 모니터링

`/dashboard` UI 표시 항목:
- 데이터 공급자 및 심볼
- KIS 공급자의 시장 세션 상태 (개장/폐장)
- 마지막 대사 시각 및 상태
- 이벤트 피드에서 대사 이벤트 앰버색 강조

## 알려진 제약사항

1. `/api/v1/live/preflight`는 다중 심볼 제공 시 첫 번째 심볼만 처리
2. KIS 미체결 주문 감지는 `hldg_qty != ord_psbl_qty` 휴리스틱 사용
3. 대사 간격은 환경변수로 설정 가능하나 YAML 설정은 미지원
