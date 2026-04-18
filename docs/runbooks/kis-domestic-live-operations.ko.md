# KIS 국내주식 라이브 운영 런북

## 사전 조건

1. KIS Open API 인증정보 환경변수 설정:
   - `TRADING_SYSTEM_KIS_APP_KEY` / `TRADING_SYSTEM_KIS_APP_SECRET`
   - `TRADING_SYSTEM_KIS_CANO` / `TRADING_SYSTEM_KIS_ACNT_PRDT_CD`
2. 선택적 재정의: `TRADING_SYSTEM_KIS_ENV`, `TRADING_SYSTEM_KIS_BASE_URL`, `TRADING_SYSTEM_KIS_MARKET_DIV`
3. dashboard/API 경로를 함께 쓸 경우 `TRADING_SYSTEM_ALLOWED_API_KEYS`도 준비한다.

## 권장 환경변수 템플릿

로컬 `.env` 또는 현재 셸 환경에 아래와 같은 구성을 준비한다.
실주문 직전까지는 `TRADING_SYSTEM_ENABLE_LIVE_ORDERS=false`를 유지한다.

```dotenv
TRADING_SYSTEM_ENV=local
TRADING_SYSTEM_TIMEZONE=Asia/Seoul

TRADING_SYSTEM_KIS_APP_KEY=your-kis-app-key
TRADING_SYSTEM_KIS_APP_SECRET=your-kis-app-secret
TRADING_SYSTEM_KIS_CANO=12345678
TRADING_SYSTEM_KIS_ACNT_PRDT_CD=01

TRADING_SYSTEM_KIS_ENV=prod
TRADING_SYSTEM_KIS_MARKET_DIV=J
# TRADING_SYSTEM_KIS_BASE_URL=
# TRADING_SYSTEM_KIS_PRICE_TR_ID=
# TRADING_SYSTEM_KIS_BALANCE_TR_ID=

TRADING_SYSTEM_ENABLE_LIVE_ORDERS=false
TRADING_SYSTEM_LIVE_BAR_SAMPLES=2
TRADING_SYSTEM_LIVE_POLL_INTERVAL=10
TRADING_SYSTEM_HEARTBEAT_INTERVAL=60
TRADING_SYSTEM_RECONCILIATION_INTERVAL=300

TRADING_SYSTEM_ALLOWED_API_KEYS=your-strong-api-key
# DATABASE_URL=postgresql://...
```

## 지원되는 실행 경로

현재 KIS 라이브 운영은 두 경로를 지원한다.

1. CLI 경로
   - `--mode live --provider kis --broker kis --live-execution preflight|paper|live`
2. API/dashboard 경로
   - `POST /api/v1/live/runtime/start`
   - `/dashboard`의 launch form

두 경로 모두 동일한 KIS 가드를 적용한다.
- `provider=kis`, `broker=kis`
- `live_execution=live`는 `TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true`일 때만 허용
- 실주문은 KRX 장 시간대에만 허용
- quote validation과 preflight를 통과해야 함

## 워크플로우: CSV 백테스트 -> KIS 프리플라이트 -> paper 리허설 -> 가드된 라이브

### 1단계: CSV 백테스트

```bash
TRADING_SYSTEM_CSV_DIR=data/market uv run -m trading_system.app.main --mode backtest --provider csv --broker paper --symbols 005930
```

백테스트가 완료되고 수익률/드로우다운 곡선이 생성되는지 확인한다.

### 2단계: KIS 프리플라이트

```bash
TRADING_SYSTEM_KIS_APP_KEY=your-key TRADING_SYSTEM_KIS_APP_SECRET=your-secret TRADING_SYSTEM_KIS_CANO=12345678 TRADING_SYSTEM_KIS_ACNT_PRDT_CD=01 uv run -m trading_system.app.main --mode live --provider kis --broker kis --symbols 005930
```

기본 `--live-execution preflight`는 실시간 KIS 현재가를 조회하고 구조화된 준비 상태 결과를 반환한다.
- `ready: true/false`
- `reasons`: 이슈 목록 (예: `market_closed`, `zero_volume`, `quote_error`)
- `quote_summary`: 종목코드, 가격, 거래량

### 3단계: paper 리허설

CLI 예시:

```bash
TRADING_SYSTEM_KIS_APP_KEY=your-key TRADING_SYSTEM_KIS_APP_SECRET=your-secret TRADING_SYSTEM_KIS_CANO=12345678 TRADING_SYSTEM_KIS_ACNT_PRDT_CD=01 uv run -m trading_system.app.main --mode live --provider kis --broker kis --symbols 005930 --live-execution paper
```

API/dashboard 예시:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/live/runtime/start   -H "Content-Type: application/json"   -H "X-API-Key: your-strong-api-key"   -d '{"mode":"live","symbols":["005930"],"provider":"kis","broker":"kis","live_execution":"paper"}'
```

이 리허설에서 실제 주문 제출 없이 session 시작, 모니터링, pause/resume/stop이 정상 동작하는지 확인한다.

### 4단계: 가드된 라이브 실행

```bash
TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true TRADING_SYSTEM_LIVE_BAR_SAMPLES=2 TRADING_SYSTEM_KIS_APP_KEY=your-key TRADING_SYSTEM_KIS_APP_SECRET=your-secret TRADING_SYSTEM_KIS_CANO=12345678 TRADING_SYSTEM_KIS_ACNT_PRDT_CD=01 uv run -m trading_system.app.main --mode live --provider kis --broker kis --symbols 005930 --live-execution live
```

**적용되는 가드:**
- `TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true` 설정 필수
- KRX 장시간만 허용 (평일 09:00-15:30 KST)
- 현재가 검증 (가격 > 0, 거래량 >= 0)

## KIS 라이브 세션 시작 전 점검 체크리스트

- [ ] KIS app key/secret, 계좌번호, 상품코드가 현재 셸 또는 `.env`에 모두 설정돼 있다
- [ ] `provider=kis`, `broker=kis`를 명시적으로 선택했다
- [ ] 첫 세션은 거래 가능한 단일 종목 1개만 사용한다
- [ ] preflight와 paper 리허설 단계에서는 `TRADING_SYSTEM_ENABLE_LIVE_ORDERS=false` 상태를 유지한다
- [ ] `preflight` 결과가 `ready=true`이고 unresolved `reasons`가 없다
- [ ] dashboard/API를 함께 사용할 경우 auth 경로(`TRADING_SYSTEM_ALLOWED_API_KEYS`)를 확인했다
- [ ] 시작 전에 stop 절차를 알고 있다 (`POST /api/v1/dashboard/control`의 `stop` 또는 dashboard Stop 버튼)

## paper 운영 리허설 체크리스트

실주문 활성화 전에 최소 1회 이상의 full paper session을 돌린다.

- [ ] 단일 종목으로 paper session을 시작했다
- [ ] dashboard status에 non-empty `session_id`가 보인다
- [ ] `controller_state=active`와 loop `state=running`이 확인된다
- [ ] `last_heartbeat`가 장시간 멈추지 않고 갱신된다
- [ ] session active 동안 `positions`, `events`, `equity` 응답이 정상적으로 갱신된다
- [ ] `portfolio.reconciliation.*` 이벤트가 비정상적으로 `skipped`에만 고정되지 않는다
- [ ] `pause`가 실제로 상태를 `paused`로 바꾼다
- [ ] `resume`이 실제로 상태를 다시 `running`으로 바꾼다
- [ ] `stop` 후 dashboard가 clean disconnected/stopped 상태로 돌아간다
- [ ] 같은 paper launch/stop 사이클을 최소 2회 반복해도 orphaned session 상태가 남지 않는다

## 첫 실주문 전 최종 게이트

paper 리허설이 안정적인 경우에만 진행한다.

- [ ] 지금 KRX 장이 열려 있다
- [ ] 단일 종목과 최소 수량으로 시작한다
- [ ] `TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true` 전환 직전에 preflight를 한 번 더 실행했다
- [ ] dashboard 접근과 stop 절차가 이미 준비돼 있다
- [ ] 첫 실주문 중 `system.control`, `system.heartbeat`, `system.error`, `order.*`, `portfolio.reconciliation.*` 이벤트를 모니터링할 수 있다
- [ ] 조금이라도 불명확한 상황이 생기면 즉시 stop 후 paper 모드로 되돌릴 계획이 있다

## 대사(Reconciliation)

라이브 루프는 `TRADING_SYSTEM_RECONCILIATION_INTERVAL`초(기본값: 300)마다 로컬 `PortfolioBook`을 KIS 브로커 잔고와 대사한다.

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
- active loop가 없을 때도 controller 상태, session id, last runtime error
- 마지막 대사 시각 및 상태
- 이벤트 피드에서 대사 이벤트 앰버색 강조

## 알려진 제약사항

1. `/api/v1/live/preflight`는 이제 다중 심볼을 지원하며, 하위 호환용 `quote_summary`와 심볼별 세부 상태용 `quote_summaries`/`symbol_count`를 함께 반환한다
2. KIS 미체결 주문 감지는 현재 브로커 잔고 스냅샷의 `ord_psbl_qty` 신호에 의존하며, held symbol에 이 값이 없으면 미체결 없음으로 가정하지 않고 fail-closed로 대사를 건너뛴다
3. 대사 간격은 YAML의 `app.reconciliation_interval`로도 선언할 수 있지만, 라이브 루프 런타임에서는 `TRADING_SYSTEM_RECONCILIATION_INTERVAL` 환경변수가 여전히 우선 override 역할을 한다
4. 아직 durable order lifecycle store는 없으므로, 첫 KIS 실주문 세션은 무인 운영이 아니라 supervised rollout로 취급하는 편이 안전하다
