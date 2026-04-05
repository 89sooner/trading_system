# 워크스페이스 분석

이 문서는 2026년 3월 28일 기준 `trading-system` 워크스페이스의 현재 구현 상태를 정리합니다.

## 저장소 상태

이 저장소는 더 이상 스캐폴드 수준이 아닙니다. 현재는 결정적 백테스트, 가드가 있는 라이브 실행 경로, FastAPI 표면, React 프론트엔드, 패턴/전략 저장소, 거래 애널리틱스, 대시보드 제어, 포트폴리오 영속화, KIS 연동까지 포함합니다.

현재 구현된 동작:

- `app.main`은 `backtest`, `live` preflight, `live` paper 실행, 명시적으로 가드된 `live` 실주문을 지원합니다.
- `app.services`는 전략 저장소, 패턴 저장소, 데이터 provider, 브로커 어댑터, 리스크 제어, 포트폴리오 영속화, 라이브 preflight 검사를 조립합니다.
- `execution.step.execute_trading_step`은 백테스트와 라이브 런타임이 공통으로 사용하는 실행 코어입니다.
- `backtest.engine.run_backtest`는 결정적 재생, 이벤트 수집, equity 추적, 다중 심볼 처리를 오케스트레이션합니다.
- `api.server`는 API key, CORS, rate-limit 미들웨어 뒤에 백테스트, 라이브 preflight, 패턴, 전략, 애널리틱스, 대시보드 라우트를 노출합니다.
- `frontend/src/routes`는 패턴 관리, 전략 프로필, 실행 결과 검토, 라이브 대시보드 모니터링을 위한 브라우저 워크플로를 제공합니다.
- `execution.reconciliation.reconcile`은 브로커가 잔고 스냅샷을 제공하는 경우 로컬 `PortfolioBook`을 브로커 상태와 맞출 수 있습니다.

## 레이어 분석

### App

앱 레이어는 CLI 인자 처리(`app.main`), 서비스 조립(`app.services`), 런타임 제어(`app.loop`)를 분리합니다.

- `--mode backtest`는 결정적 재생 경로를 실행합니다.
- `--mode live`는 기본적으로 preflight이며, paper 루프를 실행할 수 있고, KIS 전용 가드 뒤에서만 라이브 주문을 제출할 수 있습니다.
- `LiveTradingLoop`는 상태 전이, heartbeat, 대사 시도, 재시작 복구용 포트폴리오 영속화를 관리합니다.
- 대시보드 API는 루프를 직접 시작하지 않고, 연결된 live loop(`create_app(live_loop=...)`)에 의존합니다.

현재 한계:
- live loop 프로세스를 시작하고 소유하는 내장 프론트엔드/API 워크플로는 아직 없습니다.

### Data

데이터 레이어에는 현재 세 가지 구체 provider가 있습니다.

- 결정적 테스트와 스모크 시나리오용 `InMemoryMarketDataProvider`
- 파일 기반 재생을 위한 복원력 정책 포함 `CsvMarketDataProvider`
- KIS 현재가 샘플링 기반 `KisQuoteMarketDataProvider`

현재 한계:
- KIS 경로는 현재가 샘플링 기반이며, 더 풍부한 히스토리컬/라이브 데이터 어댑터 표면은 아직 없습니다.

### Strategy

전략 레이어는 예제 전략과 저장소 기반 흐름을 모두 지원합니다.

- `MomentumStrategy`는 기본 결정적 예제 전략으로 유지됩니다.
- `PatternSignalStrategy`는 학습된 패턴을 현재 윈도우와 비교해 평가합니다.
- `strategy.factory`는 inline 전략 설정이나 `configs/strategies`에 저장된 전략 프로필을 해석합니다.

현재 한계:
- 일반화된 전략 플러그인 레지스트리와 저장된 전략 프로필을 선택하는 직접적인 CLI 플래그는 아직 없습니다.

### Risk

리스크 제어는 주문 단위와 포트폴리오 단위 모두에서 동작합니다.

- `RiskLimits`는 최대 포지션, 최대 노셔널, 최대 주문 크기를 검증합니다.
- `PortfolioRiskLimits`는 세션 drawdown 보호와 롱 포지션용 SL/TP를 추가합니다.
- drawdown 비상 상황에서는 활성 심볼을 강제 청산하고 런타임 상태를 `EMERGENCY`로 전환할 수 있습니다.

현재 한계:
- 포트폴리오 정책은 의도적으로 단순하며, gross/net 노출 모델이나 더 정교한 숏 전용 리스크 프레임워크는 없습니다.

### Execution

실행 레이어는 현재 다음과 같이 명시적으로 분리되어 있습니다.

- signal-to-order adapter
- 체결 비율, 슬리피지, 수수료 정책을 가진 시뮬레이터
- retry, timeout, circuit-breaker를 가진 resilient broker wrapper
- 실주문 제출용 KIS broker adapter
- 브로커 잔고 스냅샷 기반 reconciliation helper

현재 한계:
- durable order lifecycle store가 없고, KIS reconciliation은 아직 전용 unresolved-order API가 아니라 잔고 스냅샷의 pending-order 신호에 의존합니다.

### Portfolio

`PortfolioBook`는 현재 다음을 지원합니다.

- 현금 및 포지션 갱신
- 평균 단가 추적
- 실현/미실현 손익
- 수수료 누적
- `FilePortfolioRepository`를 통한 JSON 영속화 및 재로딩

현재 한계:
- 포트폴리오 영속화는 snapshot 기반이며, event-sourced history, snapshot versioning, 외부 감사 추적은 아직 없습니다.

### Backtest

백테스트 오케스트레이션은 결정적이며, 라이브 실행과 같은 trading-step 코어를 사용합니다.

- bar는 심볼 간 병합 및 정렬됩니다.
- signal, 주문 라이프사이클 이벤트, 리스크 거절 이벤트가 직렬화됩니다.
- API는 완료된 실행 결과를 저장해 이후 조회 및 애널리틱스 검토에 사용합니다.

현재 한계:
- 백테스트는 동기 방식으로 실행되고, 실행 결과는 in-memory API repository에만 저장되므로 API 프로세스 재시작 후에는 유지되지 않습니다.

### Analytics

애널리틱스는 더 이상 cumulative return에만 한정되지 않습니다.

- 백테스트 결과 DTO는 summary, equity curve, drawdown curve를 노출합니다.
- `/api/v1/analytics/backtests/{run_id}/trades`는 거래 추출과 거래 단위 요약 통계를 제공합니다.
- 프론트엔드는 이 DTO를 기반으로 summary tile, drawdown/equity chart, trade table을 렌더링합니다.

현재 한계:
- 영속 애널리틱스 저장소나 더 넓은 노출/turnover/benchmark 리포팅 계층은 아직 없습니다.

### API와 프론트엔드

운영자 대상 애플리케이션 표면이 CLI 외에 별도로 존재합니다.

- API는 runtime, patterns, strategies, analytics, dashboard control을 다룹니다.
- 프론트엔드는 신규 실행, 저장된 실행, 패턴 세트, 전략 프로필, 대시보드 조회 라우트를 제공합니다.
- 대시보드 제어는 공식적으로 `pause`, `resume`, `reset`을 지원합니다.

현재 한계:
- `/api/v1/live/preflight`는 이제 다중 심볼을 허용하지만, 기존 소비자는 여전히 단일 `quote_summary` 필드만 가정할 수 있어 `quote_summaries`/`symbol_count`로의 전환이 필요할 수 있습니다.

## 설정과 예시

현재 설정은 두 레이어로 나뉩니다.

- `config.settings.load_settings`는 환경, 심볼, execution broker, risk, 선택적 `portfolio_risk`, backtest 필드, API CORS 설정에 대한 기본 YAML 스키마를 검증합니다.
- `app.settings.AppSettings`와 API request DTO는 `live_execution`, 전략 설정 같은 런타임 전용 필드를 검증하며, `portfolio_risk` 의미는 typed YAML loader와 공유합니다.

예시와 운영자 아티팩트:

- typed YAML 로딩용 `configs/base.yaml`
- 패턴/전략 자산 저장용 `configs/patterns/*.json`, `configs/strategies/*.json`
- 운영자 참고용 `examples/sample_backtest.yaml`, `examples/sample_backtest_krx.yaml`, `examples/sample_live_kis.yaml`

참고:

- `configs/base.yaml`과 `examples/sample_live_kis.yaml`은 이제 `portfolio_risk`와 `app.reconciliation_interval`에 대한 활성 typed 예시를 포함합니다.
- 전략 프로필과 패턴 세트 저장은 데이터베이스가 아니라 파일 기반입니다.

## 테스트 커버리지 스냅샷

현재 커버리지는 백테스트 코어뿐 아니라 운영자 표면까지 포함합니다.

- 단위 테스트: config loading, app wiring, dashboard routes, live loop behavior, KIS integration, portfolio risk, reconciliation, repositories, analytics, execution adapters
- 통합 테스트: backtest run API, pattern/strategy API flow, trade analytics API, config loader failure, API security/validation

이는 결정적 재생, 런타임 검증, 대시보드 제어, 저장소 기반 패턴/전략 워크플로에 대해 강한 회귀 기준선을 제공합니다.

## 더 넓은 프로덕션 사용 전 남은 갭

1. **Durable run storage**: 백테스트 실행 결과와 메타데이터를 위한 영속 저장소와 비동기 job 모델이 필요합니다.
2. **Frontend live orchestration**: live loop 프로세스를 시작, 연결, 관리하는 1급 UI 흐름이 아직 없습니다.
3. **Config parity**: 전략 선택과 일부 런타임 전용 필드는 아직 typed YAML loader에 완전히 반영되지 않았습니다.
4. **Exchange snapshot integration**: 일반 reconciliation 경로와 KIS balance snapshot은 연결되었지만, pending-order authority는 아직 전용 unresolved-order API가 아니라 잔고 스냅샷 신호에 의존합니다.
5. **Operational hardening**: 더 강한 auth, alerting, audit export, deployment guidance가 아직 완전 관리형 트레이딩 플랫폼 수준은 아닙니다.

## 권장 다음 백로그

1. 영속 백테스트 실행 저장소와 비동기 실행 모델을 추가합니다.
2. 특히 KIS를 포함한 브로커 연동에서 reconciliation용 unresolved/open-order source를 더 강하게 만듭니다.
3. 추가 전략 런타임 설정을 YAML의 1급 필드로 만들지, API/runtime 전용으로 유지할지 결정합니다.
4. API 서버, live loop, dashboard를 함께 시작하는 배포/운영 문서를 추가합니다.
