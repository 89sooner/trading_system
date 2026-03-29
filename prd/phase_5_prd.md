# Phase 5 PRD

관련 문서:
- 상세 구현 계획: `prd/phase_5_implementation_plan.md`
- 실행 및 검증 기록: `prd/phase_5_task.md`

## 문서 목적

이 문서는 현재 저장소의 국내주식 기능을 기준으로, 다음 구현 사이클에서 우선 개발해야 할 국내주식 관련 기능을 `Phase 5` 범위로 정의한다. 목표는 기존의 결정적 백테스트/통합 실행 구조를 유지하면서 국내주식 운영 완성도를 한 단계 높이는 것이다.

이번 버전은 바로 구현에 착수할 수 있도록 다음 항목을 명시적으로 고정한다.

- 주문 접수와 체결 의미를 어디까지 분리할지
- `pending_symbols`가 어떤 데이터 소스에서 만들어지는지
- 기존 API와 대시보드 표면을 어디까지 확장할지
- 어떤 테스트를 반드시 통과해야 Phase 5를 닫을 수 있는지

## Goal

Phase 5는 국내주식 지원을 "단일 현재가 조회 + 단순 주문 제출" 수준에서 "백테스트, 프리플라이트, 라이브 실행, 계좌/주문 동기화, 운영 검증"이 연결된 실사용 가능한 운영 기반으로 확장하는 것을 목표로 한다.

구현은 반드시 다음 원칙을 지켜야 한다.

- `src/trading_system/execution/step.py`를 백테스트와 라이브의 공통 실행 경로로 유지한다.
- 전략, 데이터, 리스크, 실행, 포트폴리오 계층을 계속 분리한다.
- 브로커 통합 세부사항은 `src/trading_system/integrations/kis.py`와 `src/trading_system/execution/kis_adapter.py` 안으로 가둔다.
- 운영자 표면은 기존 `/api/v1/live/preflight`, `/api/v1/dashboard/*`, React `/dashboard` 라우트를 확장하는 방식으로 해결한다.

## Current Baseline

- 국내주식 백테스트는 `csv` 프로바이더로 가능하다.
- 라이브 프리플라이트는 `kis` 프로바이더로 현재가 확인이 가능하다.
- 라이브 실주문은 `kis` 브로커로 현금주문 제출이 가능하다.
- KIS 데이터는 현재가를 live-like 단일 `MarketBar`로 변환하는 수준이다.
- KIS 주문 응답은 현재 `FillEvent`로 바로 축약된다.
- 브로커 계좌 스냅샷은 `cash`, `positions`, `pending_symbols`만 가지며, KIS 어댑터는 현재 `None`을 반환한다.
- reconciliation은 평균단가 외부 동기화나 브로커 미결 주문 기반 보호를 아직 제공하지 않는다.
- `/api/v1/live/preflight`는 현재 단일 심볼만 허용한다.
- 운영자 대시보드는 기존 React `/dashboard` 라우트와 `/api/v1/dashboard/status|positions|events|control` 표면을 사용한다.

## Non-Goals

- 해외주식, 선물옵션, 암호화폐 전용 기능 확장
- 초저지연 실시간 스트리밍 인프라 도입
- 새로운 브로커 추가
- 신규 operator API 또는 신규 dashboard route 추가
- `/api/v1/live/preflight`의 다중 심볼 API 확장
- 로컬 비동기 주문 상태 머신, background order-status polling loop, 로컬 order book 도입
- 주문 정정/취소 워크플로우 구현
- 공휴일/임시휴장 정밀 캘린더 도입
- 프론트엔드 대규모 재설계

## Hard Decisions

Phase 5 구현 전 다음 결정을 문서상 고정한다.

### D-1. `step.py` 경계의 브로커 계약은 유지한다

- `submit_order(order, bar) -> FillEvent` 계약은 유지한다.
- `FillEvent`는 여전히 실행 경계의 최종 입력이다.
- 접수 성공과 체결 완료를 동일 사건으로 취급하지 않도록 KIS 내부 모델을 확장하되, 공용 실행 경로는 바꾸지 않는다.

### D-2. Phase 5의 주문 상태 범위는 보수적으로 제한한다

Phase 5에서 다루는 상태는 다음으로 제한한다.

- `rejected`
- `accepted_but_unfilled`
- `partially_filled`
- `filled`

다음 항목은 후속 범위로 남긴다.

- 장기간 미체결 주문의 eventual convergence
- 주문 정정/취소 상태 머신
- 비동기 체결 추적

즉, Phase 5는 "접수되었지만 아직 체결되지 않은 주문이 포트폴리오를 왜곡하지 않도록 만드는 것"까지를 목표로 하며, 장시간 미체결 주문을 background loop로 추적하는 단계는 아니다.

### D-3. `pending_symbols`의 authoritative source를 명시한다

- `pending_symbols`는 로컬 추정값이 아니라 브로커 측 unresolved/open-order 조회 결과에서 생성한다.
- KIS 계좌 스냅샷을 만들 때는 최소한 아래 두 종류의 정보를 함께 조회해야 한다.
  - 현금/보유수량/평균단가 스냅샷
  - 미결 주문 또는 unresolved order 스냅샷
- unresolved order 조회에 실패하면 reconciliation은 fail-closed 해야 하며, 로컬 포트폴리오를 조정하지 않는다.
- "balance 조회는 성공했으니 pending 없이 그대로 reconcile" 같은 축약은 허용하지 않는다.

### D-4. 기존 API와 대시보드 표면을 확장한다

- `/api/v1/live/preflight`는 유지하되 응답을 구조화한다.
- `/api/v1/dashboard/*`는 유지하되 상태/이벤트 payload에 국내주식 운영 정보를 선택 필드로 추가한다.
- 프론트엔드는 `frontend/src/routes/dashboard.tsx`와 관련 API/types/hook을 갱신한다.
- `frontend/dashboard.html` 같은 정적 페이지는 구현 대상이 아니다.

### D-5. 설정 스키마는 반쪽 지원을 금지한다

- 새 설정이 YAML에 노출되면 `src/trading_system/config/settings.py`, 관련 테스트, `configs/`, `examples/`, `README.md`를 같은 변경에 함께 갱신한다.
- 새 설정이 아직 API/runtime-only라면 그 사실을 문서에 명확히 남기고 YAML에는 추가하지 않는다.

## Product Requirements

### PR-1. 국내주식 시세 계약 명확화

- KIS quote는 현재가 1틱을 넘어서, 라이브 루프와 프리플라이트 판단에 필요한 명시적 도메인 모델을 제공해야 한다.
- 다중 샘플 수집 시 각 샘플의 타임스탬프와 수집 의미가 로그/테스트에서 명확해야 한다.
- 0가격, 0거래량, malformed symbol, 누락 필드는 도메인 오류로 구분되어야 한다.
- CSV 기반 국내주식 백테스트는 회귀 없이 유지되어야 한다.

### PR-2. 주문 접수와 체결 의미 분리

- 주문 제출 성공만으로 체결 완료로 간주하지 않는다.
- KIS 통합 계층은 접수 메타데이터와 최종 `FillEvent` 해석을 분리한다.
- 접수되었지만 체결수량이 0인 주문은 `UNFILLED`로 표현하며 포트폴리오를 변경하지 않는다.
- 부분체결과 전량체결은 `FillStatus`로 구분되어야 한다.
- "정정 필요" 같은 운영 해석은 로그/이벤트 사유로 남기되, Phase 5에서 새로운 주문 상태 머신으로 확대하지 않는다.

### PR-3. 계좌 스냅샷과 reconciliation 완성

- 브로커 스냅샷 계약은 최소 `cash`, `positions`, `average_costs`, `pending_symbols`를 포함해야 한다.
- `pending_symbols`는 unresolved/open-order 조회를 통해 생성되어야 한다.
- 브로커 평가금액은 있더라도 Phase 5의 authoritative drift 비교 키로 사용하지 않는다.
- unresolved order 조회가 실패하거나 스냅샷이 불완전하면 reconciliation은 skip 이벤트를 남기고 로컬 상태를 조정하지 않는다.
- 외부 수동주문, 입출금, 수동 청산은 reconciliation 이벤트로 식별 가능해야 한다.

### PR-4. 국내주식 운영 가드레일

- `live_execution=live` 실주문은 평일 `09:00-15:30` KST 밖에서 차단해야 한다.
- `preflight`와 `paper`는 세션 외에도 실행할 수 있지만, readiness 결과에 `market_closed` 같은 사유를 남겨야 한다.
- 거래정지 유사 응답, 0가격, 0거래량, 비정상 호가는 주문 차단 또는 경고 사유가 되어야 한다.
- 장 세션 검증은 1차 구현에서 고정 규칙만 다루고, 공휴일 정밀 판정은 residual risk로 남긴다.

### PR-5. 운영자 가시성 강화

- 운영자는 종목별 quote 상태, 최근 주문 결과, reconciliation 드리프트 여부를 구조화 로그와 기존 dashboard/API에서 확인할 수 있어야 한다.
- `/api/v1/live/preflight`는 기존 경로를 유지하면서도 `message` 외에 readiness를 구조화된 필드로 내려줘야 한다.
- `/api/v1/dashboard/status`는 필요 시 국내주식 관련 선택 필드를 확장할 수 있어야 한다.
- `/api/v1/dashboard/events`는 국내주식 전용 이벤트를 포함해야 한다.

## Scope By Epic

### Epic A. KIS 국내주식 데이터 계약

목표:
- KIS quote를 국내주식 운영에 맞는 명시적 입력으로 정리한다.

포함:
- quote/market-state 모델 정리
- 데이터 이상치 검증
- quote-to-bar 변환 semantics 명확화
- 샘플링 의미와 로그 보강

제외:
- WebSocket 체결/호가 스트림

### Epic B. 주문 상태 보수적 현실화

목표:
- 접수와 체결을 구분하되, 공용 브로커 반환형은 유지한다.

포함:
- KIS 주문 응답 파서 확장
- acceptance metadata 모델 추가
- `FillEvent` 보수적 매핑
- 미체결/부분체결 회귀 테스트

제외:
- 비동기 order-state machine
- cancel/replace

### Epic C. 계좌 조회와 안전한 reconciliation

목표:
- 국내주식 실계좌 스냅샷과 로컬 `PortfolioBook`을 안전하게 비교한다.

포함:
- KIS 잔고/보유수량/평균단가 조회
- unresolved/open-order 조회
- `pending_symbols` 생성 규칙 고정
- average cost 동기화 규칙 명확화
- fail-closed reconciliation

### Epic D. 시장 운영 가드와 프리플라이트 확장

목표:
- 주문 전에 실행 가능성을 판단할 수 있게 한다.

포함:
- KST 장시간 가드
- 비정상 quote 차단
- `/api/v1/live/preflight` 응답 구조화
- 라이브 차단 사유 로그

### Epic E. 운영자 표면과 문서 정비

목표:
- 기존 operator surface만으로 국내주식 운영 상태를 설명 가능하게 만든다.

포함:
- `/api/v1/dashboard/*` payload 선택 필드 확장
- React `/dashboard` 관련 API/types/hook 업데이트
- README/config/example/runbook 갱신
- 국내주식 검증 runbook 추가

## Impacted Files

### Data and integration
- `src/trading_system/integrations/kis.py`
- `src/trading_system/data/provider.py`
- `src/trading_system/core/types.py`

### Execution and reconciliation
- `src/trading_system/execution/kis_adapter.py`
- `src/trading_system/execution/broker.py`
- `src/trading_system/execution/orders.py`
- `src/trading_system/execution/reconciliation.py`
- `src/trading_system/execution/step.py`

### App orchestration and settings
- `src/trading_system/app/services.py`
- `src/trading_system/app/loop.py`
- `src/trading_system/app/settings.py`
- `src/trading_system/config/settings.py`

### API and operator surface
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/routes/dashboard.py`
- `src/trading_system/api/schemas.py`
- `frontend/src/api/dashboard.ts`
- `frontend/src/api/types.ts`
- `frontend/src/hooks/useDashboardPolling.ts`
- `frontend/src/routes/dashboard.tsx`
- `frontend/src/components/dashboard/StatusCard.tsx`
- `frontend/src/components/dashboard/EventFeed.tsx`

### Portfolio and risk
- `src/trading_system/portfolio/book.py`
- `src/trading_system/risk/limits.py`
- `src/trading_system/risk/portfolio_limits.py`

### Docs, configs, examples
- `configs/base.yaml`
- `configs/krx_csv.yaml`
- `examples/`
- `README.md`
- `docs/runbooks/`

### Tests
- `tests/unit/test_kis_integration.py`
- `tests/unit/test_data_provider.py`
- `tests/unit/test_execution_adapters_and_broker.py`
- `tests/unit/test_reconciliation.py`
- `tests/unit/test_app_services.py`
- `tests/unit/test_live_loop_multi_symbol.py`
- `tests/unit/test_dashboard_routes.py`
- `tests/unit/test_config_settings.py`
- `tests/unit/test_api_backtest_schema.py`
- `tests/integration/test_config_loader_integration.py`
- 국내주식 preflight/reconciliation 관련 integration test 추가

## Delivery Slices

### Slice 0. 계약 고정

- 주문 상태 범위, `pending_symbols` 생성 규칙, preflight/dashboard 확장 범위를 문서/테스트 기준으로 고정한다.
- `/api/v1/live/preflight` 단일 심볼 제약은 유지한다.

### Slice 1. 데이터 계약

- quote 모델과 검증 규칙을 도입한다.
- quote-to-bar 변환을 명시적 함수/테스트로 분리한다.

### Slice 2. 주문 수락/체결 의미 분리

- KIS 주문 응답의 접수 메타데이터를 파싱한다.
- `FillEvent`는 보수적으로 생성한다.

### Slice 3. 계좌 스냅샷과 unresolved 주문 조회

- 잔고/보유수량/평균단가와 unresolved 주문 조회를 결합해 snapshot을 만든다.
- snapshot이 안전하지 않으면 reconciliation을 skip한다.

### Slice 4. 시장 가드와 preflight 응답 확장

- 장시간/이상 quote 검증을 추가한다.
- `/api/v1/live/preflight` 응답을 readiness 중심으로 구조화한다.

### Slice 5. 대시보드/문서/운영 절차

- dashboard status/event를 확장한다.
- React `/dashboard`와 관련 타입을 맞춘다.
- README/runbook/examples를 갱신한다.

## Success Metrics

- 국내주식 라이브 프리플라이트 실패 사유가 구조화된 readiness 필드와 로그로 식별 가능할 것
- accepted-but-unfilled 주문이 포트폴리오를 변경하지 않는 회귀 테스트가 모두 통과할 것
- reconciliation이 `average_costs`와 `pending_symbols`를 사용해 drift를 감지하거나 안전하게 skip할 것
- 기존 `/api/v1/dashboard/*`와 React `/dashboard`만으로 운영자가 국내주식 상태를 확인할 수 있을 것
- README와 runbook만으로 CSV 백테스트에서 KIS preflight까지 재현 가능할 것

## Risks and Follow-up

- KIS unresolved/open-order 응답 스펙 차이가 크면 `pending_symbols` 생성 규칙이 흔들릴 수 있다.
- 공휴일/임시휴장 캘린더가 없으므로 KST 평일 장시간 규칙만으로는 완전한 readiness를 보장하지 못한다.
- background order polling이 없기 때문에 장시간 미체결 주문의 eventual convergence는 후속 Phase 후보로 남는다.
- 주문 정정/취소, 실시간 스트리밍, 호가 기반 슬리피지 모델링은 Phase 5 범위 밖이다.
