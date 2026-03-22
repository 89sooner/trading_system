# Product Requirements Document (PRD) - Phase 3

## 1. 개요 (Overview)
Phase 1과 Phase 2를 통해 단일 실행 경로(Unified Execution path)와 상태 영속화(Persistence), 연속 라이브 루프(Live Loop) 기반이 안정적으로 구축되었습니다.
Phase 3의 목표는 이 기반 위에 **모니터링 체계, 다중 종목 확장성, 그리고 포트폴리오 수준의 리스크 방어 로직**을 추가하여 앱 수준의 프로덕트를 실제 운영 환경(Production) 수준의 견고한 시스템으로 끌어올리는 것입니다.

## 2. 세부 기능 요구사항 (Detailed Requirements)

### 2.1 실시간 라이브 대시보드 (Real-time Live Dashboard)
- **목표:** 터미널 로그 외에 시각적인 웹 UI에서 현재 백엔드의 활동 지표와 포트폴리오를 실시간 관제합니다.
- **기능 명세:**
  - **서버 상태 & 하트비트 모니터:** 대시보드 상단에 백엔드 루프의 상태(`SYNC_STATE`, `TRADING`, `PAUSED`)와 마지막 하트비트 갱신 시점을 시각적으로 표시합니다.
  - **활성 포지션 테이블:** 현재 보유 중인 종목, 진입 단가, 수량, 현재가(추정), 미실현 손익(Unrealized PnL)을 실시간 그리드로 노출합니다.
  - **이벤트(로그) 스트리밍:** 폴링(Polling) 혹은 WebSocket 연동을 통해 최근 주문/체결/에러 이벤트를 실시간 피드로 제공합니다.
  - **시스템 제어 (비상 정지):** UI에서 직접 API를 호출하여 [AppRunnerState](file:///home/roqkf/trading_system/src/trading_system/app/state.py#4-9)를 `PAUSED`로 변경(비상 정지, Kill Switch)하거나 재개(`TRADING`)할 수 있는 버튼을 제공합니다.

### 2.2 고급 리스크 및 분석 (Advanced Risk & Analytics)
- **목표:** 단일 종목 제약을 넘어 포트폴리오 전체 자산을 보호하고, 단순 수익률이 아닌 트레이드 단위의 정밀한 심층 통계를 제공합니다.
- **기능 명세:**
  - **Portfolio Drawdown Limit:** 전체 포트폴리오의 실현+미실현 손익 기준, 일일 최고점 대비 지정된 비율(-X%) 하락 시 신규 진입을 전면 차단하고 보유 포지션 강제 청산(비상 모드)으로 전환합니다.
  - **Dynamic SL/TP (Stop-Loss/Take-Profit):** 하드코딩된 전략 로직이 아닌 독립된 리스크 관리 모듈 계층에서 현재 가격을 모니터링하여 목표가/손절가 도달 시 즉각 청산 주문을 발동합니다.
  - **Trade-level Statistics:** '진입-청산' 사이클을 하나의 `Trade` 단위 객체로 묶어 승률(Win Rate), 손익비(Risk-Reward Ratio), 최대 손실폭(MDD), 평균 보유 기간(Average Time in Market) 계산 및 조회 API를 제공합니다.

### 2.3 다중 심볼 오케스트레이션 (Multi-symbol Orchestration)
- **목표:** 하나의 트레이딩 엔진 인스턴스가 여러 종목(예: `["BTCUSDT", "ETHUSDT", "SOLUSDT"]`, 다수 주식 종목)을 동시에 모니터링하고 일괄 매매할 수 있도록 확장합니다.
- **기능 명세:**
  - **다중 마켓 데이터 수집:** 라이브 루프 1회전([step.py](file:///home/roqkf/trading_system/src/trading_system/execution/step.py))마다 등록된 모든 심볼의 최신 데이터를 병렬 또는 순차적으로 fetch 합니다.
  - **심볼별 독립 전략 컨텍스트:** 각 심볼 단위로 독립된 지표(Indicator) 컨텍스트와 히스토리를 유지하여 간섭 없이 개별 Signal을 생성합니다.
  - **통합 포트폴리오 자산 배분(Allocation):** 각 심볼에서 생성된 주문이 공통된 [PortfolioBook](file:///home/roqkf/trading_system/src/trading_system/portfolio/book.py#7-103)의 가용 현금(Net Cash)을 공유하며, 현금 부족 시 우선순위 할당 체계(Allocation Logic)를 적용합니다.

### 2.4 거래소 잔고 대사 (Exchange Reconciliation)
- **목표:** [PortfolioBook](file:///home/roqkf/trading_system/src/trading_system/portfolio/book.py#7-103)의 로컬 계산 상태와 실제 증권사/거래소 계좌 잔고 간의 장부 괴리를 원천 차단합니다.
- **기능 명세:**
  - **주기적 잔고 조회:** 특정 주기마다 브로커 API를 호출하여 실제 계좌의 보유 자산과 현금(`Buying Power`) 잔고를 확인합니다.
  - **오차 보정 (Sync):** 체결 지연이나 수수료 오차액 누적으로 인해 로컬 변수와 실제 거래소 잔고에 차이가 발생할 경우, 증명된 거래소 잔고를 기준으로 로컬 모델에 보정 이벤트(Adjustment Event)를 발행하여 강제 동기화합니다.
  - **외부 입출금 자동 반영:** 사용자가 거래소 앱에서 직접 입금/출금을 진행하여 현금 잔고가 변동된 외부 요인을 자동 파악하고 포트폴리오에 반영합니다.

## 3. 기술 및 비기능 요구사항 (Non-Functional Requirements)
- **성능 (Performance):** 다중 심볼 처리 시 Network I/O 병목이 발생하지 않도록 API 호출부(Broker/Data Provider)를 비동기화(`asyncio`/`aiohttp`/`httpx`) 하는 방안을 점검 및 도입합니다.
- **관측성 (Observability):** 잔고 보정(Reconciliation) 현상과 리스크 가드레일 작동(Drawdown Limit Hit) 이벤트는 로깅 시스템에 가장 명시적인 치명도 수준(WARNING/CRITICAL)으로 기록되어 슬랙/이메일 등 외부 알림으로 확장되도록 설계합니다.
- **점진적 도입:** 위 4가지 항목을 한 번에 배포하지 않고, 개별 항목별로 단독 PR과 테스트 스위트를 구성하여 점진적(Iterative)으로 베이스라인을 올려갑니다.

## 4. 범위, 리스크 및 가정 (Scope, Risks, and Assumptions)
- **범위 (Scope):** Phase 3는 백엔드 코어 로직(리스크, 복수 종목 처리, 대사) 확장과 이를 모니터링할 프론트엔드 추가만을 대상으로 합니다. 새로운 머신러닝 모델 구축이나 별도의 이기종 블록체인 거래소(Binance 등) 어댑터는 Phase 3의 범위 밖(Out-of-scope)입니다.
- **가정 (Assumptions):** 
  - KIS API 등의 브로커 API는 주기적인 계좌 잔고(Buying Power, Position) 조회 호출(Polling)을 허용하는 충분한 Rate Limit을 제공한다.
  - Phase 1 & 2에서 구현된 `ops.py` 기반의 이벤트 추적 시스템, [LiveTradingLoop](file:///home/roqkf/trading_system/src/trading_system/app/loop.py#25-120), 그리고 [step.py](file:///home/roqkf/trading_system/src/trading_system/execution/step.py)는 Phase 3 코어 확장을 위해 안정적이고 확장 가능한 토대이다.
- **리스크 (Risks):**
  - **Reconciliation 엣지 케이스:** 주문이 전송되었으나 아직 체결 회신이 오지 않은 상태 주기(In-transit)에서 동기화를 시도하면, 로컬 모델과 브로커 잔고 간 불일치가 발생할 수 있어 보정 로직의 오류로 이어질 수 있습니다.
  - **다중 종목 자산 경합:** 여러 종목이 동시에 Signal을 낼 때 가용 현금(Cash)을 초과하는 주문이 발생할 수 있으므로, 종목 간 우선순위 결정 및 분배(Allocation) 정책의 복잡성이 큽니다.
