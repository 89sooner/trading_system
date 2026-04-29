# 현재 시스템 사용자 유즈케이스

이 문서는 2026년 4월 19일 기준 `trading_system` 워크스페이스가 지원하는 사용자 관점의 유즈케이스를 정리한 것입니다.

## 1. 범위

현재 시스템은 단일 최종 사용자용 트레이딩 제품이라기보다, 세 개의 주요 진입점을 가진 모듈형 트레이딩 워크스페이스입니다.

- 백테스트와 라이브 실행을 위한 CLI 런타임
- 백테스트, 라이브 프리플라이트, 애널리틱스, 패턴 관리, 전략 관리, 대시보드 제어를 위한 HTTP API
- 패턴/전략 관리, 백테스트 실행, 실행 결과 검토, 라이브 대시보드 모니터링을 위한 React 프론트엔드

현재 시스템은 불특정 개인 투자자보다는 운영자, 리서처, 개발자를 주요 사용자로 가정합니다.

## 2. 주요 사용자 역할

### 2.1 전략 리서처

전략 리서처는 재사용 가능한 패턴 정의를 만들고, 패턴 라벨을 실제 매매 액션에 매핑하며, 결정적 백테스트로 아이디어를 검증합니다.

### 2.2 트레이딩 운영자

트레이딩 운영자는 라이브 프리플라이트를 실행하고, 페이퍼 또는 라이브 실행을 시작하며, 런타임 상태를 모니터링하고, `emergency` 또는 `paused` 상태에 대응합니다.

### 2.3 API 또는 프론트엔드 사용자

API/프론트엔드 사용자는 Python 모듈을 직접 다루지 않고도 HTTP API와 웹 UI를 통해 저장된 아티팩트를 관리하고 결과를 조회합니다.

### 2.4 개발자 또는 시스템 통합 담당자

통합 담당자는 인프라와 워크스페이스를 연결하고, API 키/CORS/rate limit을 구성하며, 올바른 모드로 API 서버나 런타임 프로세스를 기동합니다.

## 3. 시스템 진입점

| 진입점 | 주요 목적 | 대표 사용자 |
| --- | --- | --- |
| `trading_system.app.main` | CLI에서 백테스트 또는 라이브 실행 | 운영자, 개발자 |
| `/api/v1/backtests` | 결정적 백테스트를 시작하고 실행 결과 조회 | 프론트엔드, API 클라이언트 |
| `/api/v1/backtests/dispatcher` | durable backtest queue, worker heartbeat, stale lease 상태 조회 | 운영자 |
| `/api/v1/backtests/retention/*` | 오래된 run 기록 preview/prune | 운영자, 통합 담당자 |
| `/api/v1/order-audit` | backtest run 또는 live session 기준 주문 감사 record 조회 | 운영자, 리서처 |
| `/api/v1/order-audit/export` | owner/time/status/broker id 기준 주문 감사 CSV/JSONL export | 운영자, 통합 담당자 |
| `/api/v1/live/preflight` | 라이브 실행 전 또는 실행 모드 선택 시 런타임 경로 검증 | 운영자, 통합 담당자 |
| `/api/v1/live/runtime/sessions` | live runtime session history 검색/필터/조회 | 운영자, 통합 담당자 |
| `/api/v1/live/runtime/sessions/export` | live runtime session history CSV/JSONL export | 운영자, 통합 담당자 |
| `/api/v1/live/runtime/sessions/{session_id}/evidence` | session id 기준 equity/order audit/incident evidence 조회 | 운영자, 통합 담당자 |
| `/api/v1/patterns` | 패턴 세트 학습, 저장, 목록 조회, 상세 조회 | 리서처 |
| `/api/v1/strategies` | 재사용 가능한 전략 프로필 저장 및 조회 | 리서처 |
| `/api/v1/analytics/backtests/{run_id}/trades` | 완료된 백테스트의 거래 단위 애널리틱스 조회 | 리서처 |
| `/api/v1/dashboard/*` | 활성 라이브 루프 모니터링 및 제어 | 운영자 |
| 프론트엔드 라우트 `/`, `/patterns`, `/strategies`, `/runs`, `/dashboard` | API 기반 브라우저 워크플로 | 리서처, 운영자 |

## 4. 사용자가 다루는 핵심 아티팩트

| 아티팩트 | 저장 위치 | 목적 |
| --- | --- | --- |
| 패턴 세트 | `configs/patterns/*.json` | 재사용 가능한 학습 패턴 정의 |
| 전략 프로필 | `configs/strategies/*.json` | 패턴 라벨을 매매 액션으로 매핑하는 설정 |
| 포트폴리오 스냅샷 | `data/portfolio/book.json` | 라이브 세션 재시작 시 복구 가능한 포트폴리오 상태 |
| 백테스트 실행 결과 + metadata | 파일 저장소 또는 Supabase PostgreSQL | durable한 실행 조회, 운영 문맥, 애널리틱스 |
| 라이브 runtime session history | 파일 저장소 또는 Supabase PostgreSQL | 라이브 세션 검색, export, 사후 검토 |
| 라이브 runtime event archive | 파일 저장소 또는 Supabase PostgreSQL | warning/error/risk/reconciliation/control event의 session 단위 incident review |
| 주문 감사 record | 파일 저장소 또는 Supabase PostgreSQL | run/session owner 기준 주문 생성, 체결, 거절, 리스크 거절 조회 |
| 프론트엔드 실행 이력 fallback | 브라우저 로컬 스토리지 | 백엔드가 내려간 경우를 위한 보조 캐시 |

## 5. 엔드 투 엔드 사용자 여정

현재 시스템에서 가장 가치가 큰 대표 흐름은 다음과 같습니다.

1. 라벨이 지정된 차트 예시를 정의하고 패턴 프리뷰를 학습한다.
2. 패턴 세트를 저장소 기반 설정 디렉터리에 저장한다.
3. 패턴 라벨을 `buy`, `sell`, `hold`로 매핑하는 재사용 가능한 전략 프로필을 만든다.
4. 저장된 전략 프로필을 사용해 결정적 백테스트를 실행한다.
5. 실행 요약, equity curve, drawdown, 체결, 거절, 거래 애널리틱스를 검토한다.
6. 라이브 프리플라이트를 실행해 자격 증명과 런타임 준비 상태를 확인한다.
7. 페이퍼 실행으로 이동한 뒤, 필요하면 명시적 opt-in을 통해 KIS 실주문으로 확장한다.
8. 대시보드에서 라이브 루프를 모니터링하고 필요 시 `pause`, `resume`, `reset`을 사용한다.

## 6. 상세 유즈케이스

### UC-01. 패턴 세트 프리뷰 학습

- 사용자: 전략 리서처
- 목표: 수동으로 정리한 바 시퀀스를 저장 전 단계의 후보 패턴 세트로 변환한다
- 진입점:
  - 프론트엔드 `/patterns`
  - `POST /api/v1/patterns/train`
- 선행조건:
  - 최소 1개 이상의 라벨된 예시가 있어야 한다
  - 각 예시는 최소 2개 이상의 bar를 가져야 한다
  - timestamp는 유효한 ISO datetime 문자열이어야 한다
- 주요 흐름:
  1. 사용자가 패턴 이름, 심볼, threshold, 라벨된 예시 데이터를 입력한다.
  2. 시스템은 라벨별로 예시를 그룹화한다.
  3. 각 예시 윈도우에서 feature vector를 추출한다.
  4. 라벨별 평균 벡터를 계산해 학습 패턴 프로토타입을 만든다.
  5. `pattern_set_id`, `examples_count`, 학습 패턴 목록을 포함한 프리뷰를 반환한다.
- 산출물:
  - 저장되지 않은 프리뷰 결과
  - 프론트엔드의 프리뷰 테이블
- 현재 제약:
  - 학습은 대규모 히스토리컬 데이터셋이 아니라 수동 입력 예시에 기반한다
  - 동일 라벨의 모든 예시는 같은 lookback 길이를 가져야 한다
  - 별도의 저장 단계 전까지는 어떤 결과도 영속화되지 않는다

### UC-02. 패턴 세트 저장 및 재사용

- 사용자: 전략 리서처
- 목표: 학습된 패턴 세트를 저장해 이후 전략에서 재사용할 수 있게 한다
- 진입점:
  - 프론트엔드 `/patterns`
  - `POST /api/v1/patterns`
  - `GET /api/v1/patterns`
  - `GET /api/v1/patterns/{pattern_set_id}`
- 선행조건:
  - 유효한 패턴 프리뷰 또는 저장 가능한 payload가 있어야 한다
- 주요 흐름:
  1. 사용자가 학습된 프리뷰를 저장한다.
  2. 저장소가 `configs/patterns` 아래에 JSON 파일을 기록한다.
  3. 저장된 패턴 세트는 목록과 상세 화면에서 조회 가능해진다.
- 산출물:
  - 영속 저장된 패턴 JSON 파일
  - threshold, sample 수, prototype을 보여주는 패턴 상세 화면
- 현재 제약:
  - 패턴 세트 버전 관리나 승인 절차는 아직 없다
  - 파일 기반 저장이므로 동시 편집과 라이프사이클 관리는 아직 단순한 수준이다

### UC-03. 패턴 세트 기반 전략 프로필 생성

- 사용자: 전략 리서처
- 목표: 학습된 패턴 라벨이 실제 매매 액션으로 어떻게 변환될지 정의한다
- 진입점:
  - 프론트엔드 `/strategies`
  - `POST /api/v1/strategies`
  - `GET /api/v1/strategies`
  - `GET /api/v1/strategies/{strategy_id}`
- 선행조건:
  - 최소 1개 이상의 저장된 패턴 세트가 있어야 한다
  - 최소 1개 이상의 label-to-side 매핑이 필요하다
- 주요 흐름:
  1. 사용자가 저장된 패턴 세트를 선택한다.
  2. 사용자가 `bullish=buy` 같은 `label_to_side` 매핑을 정의한다.
  3. 필요하면 라벨별 threshold와 trade quantity를 오버라이드한다.
  4. 시스템이 전략 프로필 JSON을 `configs/strategies` 아래에 저장한다.
- 산출물:
  - `strategy_id`로 참조 가능한 재사용 전략 프로필
- 현재 제약:
  - 저장되는 프로필은 profile 참조 중첩이 아니라 inline pattern strategy 설정만 사용해야 한다
  - API/UI 흐름에서 지원되는 전략 타입은 현재 `pattern_signal` 하나뿐이다

### UC-04. 결정적 백테스트 실행

- 사용자: 전략 리서처 또는 API 사용자
- 목표: 전략 동작을 결정적 재생 방식으로 검증한다
- 진입점:
  - 프론트엔드 `/`
  - CLI `--mode backtest`
  - `POST /api/v1/backtests`
- 선행조건:
  - 시장 데이터 provider가 준비되어 있어야 한다: `mock`, `csv`, `kis`
  - 리스크 및 백테스트 파라미터가 유효해야 한다
  - pattern strategy를 쓰는 경우 참조하는 패턴 세트 또는 전략 프로필이 존재해야 한다
- 주요 흐름:
  1. 사용자가 심볼, 수량, 수수료, 리스크 한도를 제출한다.
  2. 시스템은 strategy, provider, broker simulator 또는 KIS adapter, portfolio, logging을 포함한 서비스를 구성한다.
  3. 히스토리컬 또는 mock bar를 불러와 timestamp 순으로 병합한다.
  4. 각 bar는 통합 실행 스텝을 통과한다.
     strategy evaluation -> signal -> order mapping -> risk check -> broker fill -> portfolio update
  5. equity point, order, signal, risk rejection 이벤트를 수집한다.
  6. 주문 생성/체결/거절/리스크 거절은 run owner 기준 order audit record로 저장된다.
  7. API는 durable job record를 저장하고 dispatcher 또는 CLI worker가 작업을 claim해 `queued`, `running`, `succeeded`, `failed`, `cancelled` 상태로 갱신한다.
- 산출물:
  - 수익률 요약 지표
  - equity curve
  - drawdown curve
  - signal, order, rejection 이벤트 스트림
- 현재 제약:
  - API-owned dispatcher와 별도 CLI worker가 같은 durable job contract를 사용하지만, 외부 queue 서비스와 부분 결과 resume은 아직 없다
  - 영속화 방식은 배포 설정에 따라 달라진다: 기본은 파일 기반, `DATABASE_URL` 설정 시 Supabase 기반
  - 프론트엔드의 새 실행 화면은 단일 심볼 입력만 받지만, 내부 백테스트 엔진은 다중 심볼 처리도 가능하다
  - CLI 경로는 `--strategy-profile-id`와 `--config`로 저장된 pattern strategy profile을 선택할 수 있다

### UC-05. 백테스트 결과 및 거래 애널리틱스 검토

- 사용자: 전략 리서처
- 목표: 해당 실행이 다음 반복 실험이나 승격 대상으로 적절한지 판단한다
- 진입점:
  - 프론트엔드 `/runs`
  - 프론트엔드 `/runs/{runId}`
  - `GET /api/v1/backtests/{run_id}`
  - `GET /api/v1/analytics/backtests/{run_id}/trades`
- 선행조건:
  - 백테스트 실행 결과가 존재하고 `succeeded` 상태이며, 현재 설정된 repository에서 조회 가능해야 한다
- 주요 흐름:
  1. 사용자가 실행 이력 또는 실행 상세 화면을 연다.
  2. 시스템이 저장된 실행 결과를 불러온다.
  3. 실행이 성공 상태라면 order 이벤트에서 거래를 추출하고 요약 통계를 계산한다.
  4. 프론트엔드는 요약 타일, 차트, 신호, 체결/거절, 거래 테이블을 렌더링한다.
- 산출물:
  - 실행 단위 요약: return, drawdown, volatility, win rate
  - 거래 단위 요약: trade count, win rate, risk/reward, max drawdown, 평균 보유 시간
- 현재 제약:
  - 서버 저장소가 이제 run history의 primary source이지만, 백엔드 장애 시를 대비한 브라우저 fallback cache는 여전히 존재한다
  - run review는 route/strategy metadata를 보여주지만, promotion/approval workflow는 아직 없다

### UC-06. 안전한 라이브 프리플라이트 실행

- 사용자: 트레이딩 운영자
- 목표: 실제 실행 전에 라이브 런타임 의존성과 자격 증명이 정상인지 확인한다
- 진입점:
  - CLI `--mode live --live-execution preflight`
  - `POST /api/v1/live/preflight`
- 선행조건:
  - 필요한 자격 증명이 존재해야 한다
  - provider 또는 broker가 `kis`인 경우 KIS 자격 증명이 설정되어 있어야 한다
  - 라이브 API 런타임에는 최소 1개의 심볼이 전달되어야 한다
- 주요 흐름:
  1. 사용자가 preflight 모드로 라이브 실행을 요청한다.
  2. 시스템이 런타임 설정과 필요한 secret을 검증한다.
  3. KIS를 사용하는 경우 심볼별 quote preflight를 수행한다.
  4. 시스템은 성공 메시지를 반환하고 주문은 제출하지 않는다.
- 산출물:
  - 운영자가 읽을 수 있는 preflight 성공/실패 메시지
- 현재 제약:
  - 기존 소비자는 단일 `quote_summary` 필드만 가정할 수 있으므로, 다중 심볼 세부 상태는 `quote_summaries`/`symbol_count`로 읽는 쪽으로 전환해야 한다
  - preflight는 provider/broker 연결 경로를 검증하지만, 완전한 배포 준비 체크리스트는 아니다

### UC-07. 라이브 페이퍼 실행

- 사용자: 트레이딩 운영자
- 목표: 실제 주문 없이도 라이브 루프를 현실적인 상태 전이로 실행한다
- 진입점:
  - CLI `--mode live --live-execution paper`
  - `POST /api/v1/live/preflight` with `live_execution=paper`
- 선행조건:
  - 라이브 preflight가 통과해야 한다
  - provider와 broker 경로가 준비되어 있어야 한다
- 주요 흐름:
  1. 라이브 루프가 `RUNNING` 상태로 시작된다.
  2. 각 poll interval마다 설정된 심볼의 새 bar를 로드한다.
  3. 통합 trading step이 mark 갱신, 리스크 평가, signal 발생, 체결 시뮬레이션을 수행한다.
  4. 포트폴리오 상태를 `data/portfolio/book.json`에 저장한다.
  5. heartbeat와 런타임 이벤트를 기록해 대시보드에서 조회할 수 있게 한다.
- 산출물:
  - 연속적인 포트폴리오 상태
  - 최근 이벤트 스트림
  - 재시작 복구 가능한 포트폴리오 스냅샷
- 현재 제약:
  - 과거 live session은 `/dashboard/sessions`에서 검색과 evidence review가 가능하지만, 오래된 session retention/prune 정책은 아직 없다
  - 페이퍼 실행은 라이브와 같은 루프 메커니즘을 공유하며, API 프로세스는 한 번에 하나의 active runtime session만 소유한다
  - 라이브 대시보드는 활성 루프가 `app.state.live_loop`에 연결된 상태로 API 서버가 실행될 때만 동작한다

### UC-08. KIS를 통한 실주문 라이브 실행

- 사용자: 트레이딩 운영자
- 목표: 명시적 안전장치 아래에서 페이퍼 실행을 실제 브로커 주문 제출로 확장한다
- 진입점:
  - CLI `--mode live --provider kis --broker kis --live-execution live`
  - `POST /api/v1/live/preflight` with `live_execution=live`
- 선행조건:
  - provider와 broker가 모두 `kis`여야 한다
  - KIS 자격 증명이 존재해야 한다
  - `TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true`
  - KIS live bar sample 수는 최소 2 이상으로 해석되어야 한다
- 주요 흐름:
  1. 사용자가 명시적으로 live execution을 opt-in 한다.
  2. 시스템이 KIS 전용 라우팅과 라이브 주문 활성화 환경 변수를 검증한다.
  3. 라이브 루프는 여전히 통합 step 경로를 사용하지만, broker delegate는 KIS adapter가 된다.
  4. 주문은 simulator가 아니라 broker adapter를 통해 제출될 수 있다.
- 산출물:
  - KIS adapter를 통한 실제 브로커 주문 흐름
  - 영속 포트폴리오 상태와 구조화 이벤트 로그
- 현재 제약:
  - 실주문은 의도적으로 강한 게이트 뒤에 놓여 있다
  - 풍부한 주문 수명주기 복구, 알림 라우팅, durable order state 같은 운영 보호 장치는 아직 제한적이다

### UC-09. 라이브 런타임 모니터링 및 제어

- 사용자: 트레이딩 운영자
- 목표: 코드를 수정하지 않고 런타임 상태를 점검하고 개입한다
- 진입점:
  - 프론트엔드 `/dashboard`
  - `GET /api/v1/dashboard/status`
  - `GET /api/v1/dashboard/positions`
  - `GET /api/v1/dashboard/events`
  - `GET /api/v1/dashboard/equity`
  - `GET /api/v1/dashboard/stream`
  - `POST /api/v1/dashboard/control`
- 선행조건:
  - 라이브 루프가 연결된 API 서버가 실행 중이어야 한다
- 주요 흐름:
  1. 대시보드는 서버에서 최근 equity 이력을 먼저 읽고, 라이브 업데이트를 위해 SSE 스트림을 연다.
  2. SSE 연결이 끊기면 UI는 status, positions, events에 대해 5초 polling fallback으로 전환한다.
  3. 운영자는 루프 상태, heartbeat freshness, cash, positions, unrealized PnL, 최근 이벤트, equity curve를 확인한다.
  4. 운영자는 `pause`, `resume`, `reset`을 보낼 수 있다.
  5. 시스템은 유효한 상태 전이만 적용하고 control 이벤트를 로그에 남긴다.
- 산출물:
  - 실시간 운영 가시성
  - 제한된 런타임 제어 표면
- 현재 제약:
  - `reset`은 `EMERGENCY`를 `PAUSED`로만 되돌린다
  - 잘못된 전이나 no-op 전이는 현재 상태와 함께 성공 응답을 반환한다
  - 대시보드에는 직접적인 `stop`, `liquidate-all`, 파라미터 수정 기능이 없다

### UC-10. 내부 보안 API로 시스템 사용

- 사용자: API 사용자 또는 통합 담당자
- 목표: 기본적인 운영 안전장치를 유지하면서 외부 도구에서 워크스페이스를 사용한다
- 진입점:
  - 모든 HTTP API 라우트
- 선행조건:
  - API 서버가 프로젝트 환경에서 실행 중이어야 한다
  - API key 검증이 활성화된 경우 호출자가 올바른 키를 가져야 한다
- 주요 흐름:
  1. 호출자가 FastAPI 서버에 요청을 보낸다.
  2. 미들웨어가 CORS 규칙, correlation ID, API key 검증, 단순 rate limit을 적용한다.
  3. 라우트 핸들러가 성공 응답용 typed DTO와 검증/런타임 오류용 구조화 응답을 반환한다.
- 산출물:
  - UI나 자동화 클라이언트가 사용할 수 있는 안정적인 JSON 응답
- 현재 제약:
  - 현재 보안 수준은 내부 서비스 경계에는 적합하지만, 인터넷 공개 배포용으로는 아직 강화가 부족하다
  - rate limiting은 프로세스 메모리 기반이다

## 7. 사용자가 기대해야 할 공통 동작

### 7.1 통합 실행 경로

백테스트와 라이브 실행은 모두 같은 `execute_trading_step` 흐름을 사용합니다. 따라서 strategy evaluation, risk check, order mapping, portfolio mutation이 시뮬레이션과 라이브 지향 런타임에서 일관되게 동작합니다.

### 7.2 안전 중심 기본값

시스템은 가능한 한 가장 안전한 런타임 자세를 기본값으로 둡니다.

- CLI 라이브 모드의 기본값은 `preflight`
- 실주문은 명시적인 `live` 모드와 환경 변수 활성화가 모두 필요
- 대시보드는 일시정지나 emergency 복구는 가능하지만, 자동으로 바로 라이브 거래 상태로 되돌리지는 않음

### 7.3 결정적이고 해석 가능한 출력

백테스트 결과는 불투명한 블랙박스 결과가 아니라 분석 가능한 형태로 제공됩니다.

- 이벤트 스트림이 직렬화된다
- 숫자 필드는 JSON 전송을 위해 일관되게 문자열화된다
- 차트와 요약 타일은 typed DTO를 기반으로 재구성된다

## 8. 현재 제품 경계와 갭

현재 구현은 리서치, 통제된 페이퍼 트레이딩, 운영자 중심 모니터링에는 강하지만, 완전한 프로덕션 트레이딩 플랫폼은 아닙니다.

사용자가 감안해야 할 주요 갭은 다음과 같습니다.

- 장시간 백테스트를 위한 외부 queue/분산 worker 모델이 없음
- 공유 API key 검증 외의 다중 사용자 auth 모델이 없음
- 고급 주문 수명주기 대시보드와 broker별 미체결 주문 제어가 없음
- 전략 마켓플레이스, 승인 워크플로, 승격 파이프라인이 없음
- 내장 order audit export는 bounded CSV/JSONL 응답이며, 대량 비동기 export pipeline은 없음

## 9. 권장 후속 문서

운영 관점에서 다음 문서들이 추가되면 가치가 큽니다.

1. API 서버와 라이브 루프를 함께 기동하는 방법을 설명하는 라이브 배포 가이드
2. 예시 입력 형식과 라벨링 규칙을 설명하는 패턴 작성 가이드
3. 패턴 프리뷰 -> 저장 전략 -> 백테스트 -> 페이퍼 -> 라이브 승격 체크리스트
