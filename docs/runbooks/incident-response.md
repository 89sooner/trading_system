# Incident runbook

## Scope

운영 경계 계층(`app`, `data`, `execution`)에서 발생하는 장애를 빠르게 분류하고 복구한다.
모든 로그는 구조화 포맷(JSON 또는 key-value)과 `correlation_id`를 포함한다.

## 공통 점검 절차

1. `correlation_id` 기준으로 `order.created`, `order.rejected`, `order.filled`, `risk.rejected`, `exception` 이벤트를 시간순으로 조회한다.
2. 민감정보(`api_key`, `token`, `password`, `secret`)가 로그에 마스킹(`***`)되었는지 확인한다.
3. 외부 I/O 경계(`data` 공급자, `execution` 브로커 어댑터)의 재시도/타임아웃/서킷브레이커 상태를 확인한다.

## 시나리오 A: 데이터 끊김(data disconnect)

증상:
- `data.load.success` 이벤트가 중단됨
- `exception` 이벤트에서 파일/네트워크 I/O 오류 증가

대응:
1. 데이터 소스 접근성 확인(파일 경로, 네트워크, 권한).
2. 서킷브레이커 열림 여부 확인. 열려 있으면 `reset_timeout_seconds` 경과 후 재시도.
3. 장애 구간을 건너뛰지 말고 재수집 후 재실행(결정론 보존).

## 시나리오 B: 주문 실패(order failure)

증상:
- `order.rejected` 급증
- `order.filled` 감소

대응:
1. `reason=risk_limits` 인지 `reason=unfilled` 인지 구분.
2. `risk.rejected` 이벤트의 `requested_quantity/current_position/price`를 검토해 제한값 재검증.
3. 브로커 경계의 재시도 횟수와 타임아웃을 확인해 중복 주문이 없는지 점검.

## 시나리오 C: 시계열 지연(time-series lag)

증상:
- 바 타임스탬프와 처리 시각의 차이가 증가
- 전략 평가 주기 누락

대응:
1. 지연 구간의 원본 데이터 타임존/포맷 검증(UTC, DST 변환 확인).
2. 지연 원인이 데이터 경계인지 실행 경계인지 분리.
3. 지연 허용 임계치 초과 시 주문 생성 중단 후 알림, 데이터 정상화 후 재개.

## 시크릿 운영 원칙

- API 키는 `TRADING_SYSTEM_API_KEY` 같은 환경변수 또는 시크릿 매니저에서만 주입한다.
- 코드 저장소, 설정 파일, 로그, 티켓에 시크릿을 남기지 않는다.
