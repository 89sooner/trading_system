# Incident runbook

## Scope

운영 경계 계층(`app`, `api`, `data`, `execution`, `portfolio`)에서 발생하는 장애를 빠르게 분류하고 복구한다.
모든 로그는 구조화 포맷(JSON 또는 key-value)과 `correlation_id`를 포함한다.

## 공통 점검 절차

1. `correlation_id` 기준으로 `system.error`, `system.heartbeat`, `system.control`, `order.created`, `order.rejected`, `order.filled`, `risk.rejected`, `risk.daily_limit_breached`, `portfolio.reconciliation.*` 이벤트를 시간순으로 조회한다.
2. 민감정보(`api_key`, `token`, `password`, `secret`)가 로그에 마스킹(`***`)되었는지 확인한다.
3. 외부 I/O 경계(`data` 공급자, `execution` 브로커 어댑터)의 재시도/타임아웃/서킷브레이커 상태를 확인한다.
4. 대시보드가 연결된 환경이면 `/api/v1/dashboard/status`, `/api/v1/dashboard/events` 결과와 로그 이벤트를 함께 대조한다.
5. 종료된 session은 `/dashboard/sessions` 또는 `/api/v1/live/runtime/sessions/<session_id>/evidence`에서 archived runtime incident, equity point count, live-session order audit record를 함께 대조한다.

## 시나리오 A: 데이터 끊김(data disconnect)

증상:
- `data.load.success` 이벤트가 중단됨
- `system.error` 이벤트에서 CSV/KIS 또는 브로커 호출 관련 오류 증가
- 라이브 preflight 또는 paper loop가 반복적으로 일시정지됨

대응:
1. 데이터 소스 접근성 확인(파일 경로, 네트워크, 권한).
2. 서킷브레이커 열림 여부 확인. 열려 있으면 `reset_timeout_seconds` 경과 후 재시도.
3. KIS 경로라면 인증정보, `TRADING_SYSTEM_KIS_BASE_URL`, `TRADING_SYSTEM_KIS_MARKET_DIV`, 네트워크 상태를 함께 점검한다.
4. 장애 구간을 건너뛰지 말고 재수집 후 재실행(결정론 보존).

## 시나리오 B: 리스크 거절(risk rejection) 또는 비상 정지(emergency)

증상:
- `risk.rejected` 급증
- `risk.daily_limit_breached`, `risk.emergency_liquidation`, `risk.sl_triggered`, `risk.tp_triggered` 이벤트 발생
- 대시보드 상태가 `EMERGENCY` 또는 `PAUSED`로 유지됨

대응:
1. `risk.rejected`와 `order.rejected`를 구분해 원인이 리스크 가드인지 체결 실패인지 먼저 분리한다.
2. `risk.rejected` payload의 `requested_quantity`, `current_position`, `price`를 검토해 `max_position`, `max_notional`, `max_order_size`를 재검증한다.
3. `risk.daily_limit_breached`가 발생한 경우 현재 세션 peak equity와 손실 구간을 확인하고, `reset` 전에는 원인과 포지션 상태를 먼저 점검한다.
4. `sl_pct` 또는 `tp_pct`를 사용하는 경우 평균 단가와 mark 가격 계산이 운영 기대와 일치하는지 확인한다.

## 시나리오 C: 주문 실패(order failure) 또는 브로커 오류

증상:
- `order.rejected` 증가
- `system.error`에서 브로커 제출 오류, 타임아웃, HTTP/transport 오류가 관측됨
- `order.created`는 있으나 `order.filled`가 기대보다 적음

대응:
1. 시뮬레이터 경로라면 `order.rejected`가 `unfilled`인지 확인하고 fill policy 설정을 재검토한다.
2. KIS 경로라면 인증정보, `tr_id`, 네트워크, base URL, 시장 구분 코드 설정을 확인한다.
3. 재시도/타임아웃 이후 외부에서 중복 주문이 실제로 발생하지 않았는지 브로커 측 주문 내역을 점검한다.
4. 원인이 미확정이면 대시보드에서 `pause` 후 상태를 고정하고 로그를 수집한다.

## 시나리오 C-2: Live order stale 또는 취소 실패

증상:
- `live_order.stale`, `live_order.gate_blocked`, `live_order.cancel_failed` 이벤트 발생
- dashboard Open orders 패널에 `stale`, `unknown`, `cancel_requested` 상태가 유지됨
- `portfolio.reconciliation.skipped`가 `active_live_order` 사유로 반복됨

대응:
1. Open orders 패널 또는 `/api/v1/dashboard/orders`에서 `broker_order_id`, `remaining_quantity`, `last_synced_at`, `last_error`를 확인한다.
2. KIS 주문 내역에서 해당 `broker_order_id`의 실제 체결/취소 상태를 대조한다.
3. 취소가 필요한 경우 dashboard cancel action 또는 `/api/v1/dashboard/orders/<record_id>/cancel`을 사용한다.
4. 취소 실패 또는 상태 불명확이 계속되면 live loop를 `pause` 또는 `stop`하고 브로커 상태를 수동 확정한 뒤 재개한다.

## 시나리오 D: 대사(reconciliation) 불일치

증상:
- `portfolio.reconciliation.cash_adjusted`
- `portfolio.reconciliation.position_adjusted`
- `portfolio.reconciliation.cash_frozen`
- `portfolio.reconciliation.symbol_skipped`

대응:
1. 현재 브로커가 계좌 스냅샷을 제공하는 경로인지 먼저 확인한다.
2. `cash_frozen` 또는 `symbol_skipped`가 발생하면 `pending_symbols`에 기록된 심볼의 체결 중 상태를 우선 확인한다.
3. 포지션 차이가 설명되지 않으면 루프를 `pause`한 뒤 로컬 `PortfolioBook`과 브로커 상태를 수동 대조한다.
4. 현재 KIS 어댑터는 미체결/open-order snapshot을 먼저 조회하고, 잔고 스냅샷을 이어서 조회한다. `pending_source=open_orders` 상태에서 건너뛰었다면 broker order id 기준으로 `/api/v1/order-audit/export` 결과와 KIS 주문 내역을 대조한다.
5. open-order 조회 실패로 `portfolio.reconciliation.skipped`가 발생하면 포트폴리오를 자동 보정하지 않는다. KIS 응답 필드, TR ID, 네트워크 상태를 먼저 확인한다.

## 시크릿 운영 원칙

- API 키는 `TRADING_SYSTEM_API_KEY` 같은 환경변수 또는 시크릿 매니저에서만 주입한다.
- KIS 자격증명은 `TRADING_SYSTEM_KIS_APP_KEY`, `TRADING_SYSTEM_KIS_APP_SECRET`, `TRADING_SYSTEM_KIS_CANO`, `TRADING_SYSTEM_KIS_ACNT_PRDT_CD`로만 주입한다.
- 코드 저장소, 설정 파일, 로그, 티켓에 시크릿을 남기지 않는다.
