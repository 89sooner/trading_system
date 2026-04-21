# 아키텍처 개요

현재 아키텍처는 명시적인 레이어와 운영 표면을 기준으로 나뉘어 있습니다.

- `app`: CLI 진입점, 서비스 조립, 라이브 루프 런타임
- `api`: HTTP 라우트, 대시보드 연결, 보안 미들웨어
- `patterns`: 패턴 학습, 매칭, 알림, 저장소
- `data`: 시장 데이터 모델과 provider 인터페이스
- `strategy`: 신호 생성과 전략 계약
- `risk`: 포지션 및 주문 검증
- `execution`: 주문 요청과 브로커 인터페이스
- `portfolio`: 보유 상태, 현금 상태, 영속 저장소
- `backtest`: 과거 데이터 기반 오케스트레이션
- `analytics`: 성과 지표와 리포팅 보조 기능
- `integrations`: KIS 같은 외부 클라이언트

권장 흐름:

1. 데이터 provider가 bar, tick, snapshot을 전달한다.
2. 전략이 원하는 액션을 생성한다.
3. 리스크 관리가 해당 액션을 검증한다.
4. 실행 계층이 액션을 주문 요청으로 변환한다.
5. 포트폴리오 상태는 체결 결과를 반영하고 필요 시 디스크에 저장된다.
6. 애널리틱스 계층이 이벤트 스트림 기반 성과 지표를 계산한다.

현재 구현 메모:

- 저장소는 백테스트와 라이브 루프 모두에서 공통 실행 코어(`execute_trading_step`)를 사용한다.
- HTTP API는 같은 런타임 서비스 위에서 백테스트, 패턴/전략 관리, 애널리틱스, admin 키 관리, `/health`, 대시보드 제어, live runtime session history를 노출한다.
- 라이브 트레이딩은 상태 제어(`AppRunnerState`), heartbeat 로깅, 정상 종료를 포함한 `LiveTradingLoop`로 관리된다.
- 포트폴리오 상태는 라이브 세션 재시작 복구를 위해 `book.json`에 저장되며, 백테스트 런, run metadata, 대시보드 equity 이력, live runtime session history는 `DATABASE_URL` 유무에 따라 파일 기반 또는 Supabase PostgreSQL 기반으로 영속화된다.
- 백테스트 런은 provider, broker, strategy profile, pattern set, source, notes 같은 운영 메타데이터를 함께 저장한다.
- 저장소 기반 API key는 disabled 상태와 last-used 추적 같은 기본 거버넌스 필드를 가진다.
- 선택된 런타임 이벤트는 bounded worker 기반 webhook 알림으로 외부에 전달할 수 있다.
