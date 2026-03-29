# Phase 5 PRD 문서 리뷰 (Claude)

리뷰 대상:
- `prd/phase_5_prd.md`
- `prd/phase_5_implementation_plan.md`
- `prd/phase_5_task.md`

리뷰 일자: 2026-03-28

---

## 1. 전체 평가

세 문서의 역할 분담이 명확하다: PRD(what/why) → Implementation Plan(how/order) → Task(tracking). Codex가 현재 코드베이스를 상당히 정확하게 파악하고 작성했다.

---

## 2. 정확하게 반영된 부분

| 항목 | 근거 |
|------|------|
| `step.py`를 authoritative execution path로 유지 | 현재 `execute_trading_step()`이 전략→주문→체결→포트폴리오 전체 흐름을 제어함 |
| `submit_order(order, bar) -> FillEvent` 계약 유지 | `broker.py`의 `BrokerSimulator` 프로토콜과 정확히 일치 |
| `AccountBalanceSnapshot`에 `average_costs` 미존재 | 현재 `cash`, `positions`, `pending_symbols`만 있음 확인 |
| `KisBrokerAdapter.get_account_balance()` → `None` 반환 | 현재 stub 상태 정확 |
| `FillStatus` enum: FILLED, PARTIALLY_FILLED, UNFILLED | `broker.py`에 이미 정의되어 있음 |
| `/api/v1/live/preflight` 단일 심볼 제약 | `backtest.py`에서 live 모드일 때 `len(symbols) != 1` 검증 존재 |
| 신규 route 없이 기존 dashboard 확장 | 현재 `/api/v1/dashboard/*` 4개 엔드포인트 존재 확인 |
| CSV backtest 회귀 방지 | `CsvMarketDataProvider`는 독립 경로이므로 격리 가능 |

---

## 3. 문제점 및 개선 필요 사항

### 3.1 코드 현실과 불일치하는 부분

#### A. `FillStatus`에 대한 오해 가능성

PRD D-2에서 Phase 5 상태를 `rejected`, `accepted_but_unfilled`, `partially_filled`, `filled`로 정의하지만, 현재 `FillStatus` enum은 `FILLED`, `PARTIALLY_FILLED`, `UNFILLED` 3가지만 있다. `REJECTED`가 없다.

현재 코드에서 주문 거부는 `step.py`에서 `RiskLimits` 검증 실패 시 `StepEvents.risk_rejected`로 처리되며, 브로커 레벨의 rejection은 별도 상태가 아니다. PRD에서 `rejected`를 `FillStatus`에 추가할 것인지, 아니면 KIS 내부 모델에만 둘 것인지 명시해야 한다.

**권장**: PRD D-2에 "`rejected`는 KIS 내부 모델에서만 구분하며, 공용 `FillStatus`에는 추가하지 않는다" 또는 "추가한다"를 명확히 기술

#### B. `step.py`의 `filled_quantity == 0` 처리 현실

PRD는 "filled_quantity > 0일 때만 PortfolioBook 변경"을 규칙으로 명시한다. 현재 `step.py`에서 실제 동작을 보면:

```python
# step.py 현재 코드
if fill.filled_quantity > 0:
    portfolio.apply_fill(...)
```

이 부분은 이미 구현되어 있어서 Phase 5에서 새로 할 일이 아니다. PRD가 "이 규칙을 회귀 테스트로 **고정**"이라고 했으므로 의도는 맞지만, 현재 이미 존재한다는 사실을 baseline에 기록하는 것이 좋다.

#### C. `KisQuoteMarketDataProvider`의 multi-sample 동작

Implementation Plan Step 1에서 "multi-sample load 테스트 추가"라고 했지만, 현재 `KisQuoteMarketDataProvider`는 `bars_per_load` 파라미터로 N번 `preflight_symbol()`을 호출하여 N개 bar를 생성한다. 각 bar의 timestamp가 모두 같은 시각(`datetime.now()`)으로 찍히는 문제가 있는데, PRD에서 이를 구체적으로 어떻게 해결할지(각 sample마다 실제 호출 시각을 사용할지, interval을 두고 호출할지) 언급이 없다.

**권장**: PR-1에 "multi-sample 수집 시 각 sample의 timestamp는 실제 API 호출 시점을 사용한다" 같은 구체적 semantics 추가

### 3.2 누락된 설계 결정

#### D. `KisOrderResult` 확장 범위 미구체

PRD는 "receipt metadata를 보존"이라고 하지만, KIS 국내주식 주문 API 응답에서 어떤 필드들을 receipt metadata로 간주할지 구체적이지 않다. 현재 `_parse_order_response()`는 `ODNO`(주문번호), `ORD_QTY`(주문수량), `ORD_UNPR`(주문단가)만 파싱한다.

**권장**: 다음 중 어떤 필드를 추가할지 명시 필요
- `ord_dt`(주문일자), `ord_tmd`(주문시각)
- KIS 응답의 `rt_cd`(성공/실패 코드), `msg_cd`, `msg1`
- 체결 관련: `tot_ccld_qty`(총체결수량), `tot_ccld_amt`(총체결금액)

#### E. KIS Balance/Holdings API 스펙 미기술

Implementation Plan Step 3에서 "KIS balance/holdings/average-costs 조회 추가"라고 했지만, 어떤 KIS API를 호출할지 구체적이지 않다. KIS 국내주식 API에는:
- 잔고조회: `/uapi/domestic-stock/v1/trading/inquire-balance`
- 미체결조회: `/uapi/domestic-stock/v1/trading/inquire-psbl-order` 또는 `/inquire-daily-ccld`

**권장**: Implementation Plan에 사용할 KIS API endpoint path와 응답 필드 매핑을 명시

#### F. Reconciliation skip의 구현 위치

PRD D-3과 Implementation Plan Step 3에서 "snapshot이 불완전하면 reconcile skip"이라고 했지만, skip을 어디서 결정할지가 모호하다:
- `KisBrokerAdapter.get_account_balance()`가 `None`을 반환 → 현재 `loop.py`의 `_maybe_reconcile()`에서 `if snapshot:`로 이미 처리
- 부분 성공(balance 성공 + unresolved order 실패)일 때는?

현재 `_maybe_reconcile()`는 snapshot이 `None`이면 skip하지만 이벤트를 남기지 않는다.

**권장**: "KisBrokerAdapter가 불완전 snapshot을 None으로 반환하고, loop.py가 skip 이벤트를 로깅한다"처럼 책임 분배를 명시

### 3.3 Frontend 관련 미흡 사항

#### G. Dashboard DTO 확장 필드의 구체 스펙

PRD D-4에서 dashboard status payload에 추가할 optional 필드를 나열했지만:
- `provider`, `symbols`, `market_session`, `last_reconciliation_at`, `last_reconciliation_status`

현재 `DashboardStatusDTO`는 `state`, `last_heartbeat`, `uptime_seconds`만 있다. 이 필드들의 타입과 null 허용 여부가 명시되지 않았다.

**권장**: `phase_5_implementation_plan.md`에 DTO 확장 스펙을 Pydantic 모델 수준으로 구체화

#### H. Frontend 컴포넌트 파일 범위

Implementation Plan Step 5에서 `StatusCard.tsx`와 `EventFeed.tsx`를 언급하지만, 현재 컴포넌트 디렉토리 구조와 실제 import 관계를 확인하면:
- `frontend/src/components/dashboard/StatusCard.tsx` - 존재
- `frontend/src/components/dashboard/EventFeed.tsx` - 존재
- `frontend/src/components/dashboard/PositionsTable.tsx` - 존재하지만 PRD에 미포함

Positions에 `average_cost` 필드가 이미 있으므로, reconciliation 후 average_cost 변경이 positions 테이블에도 반영되는지 확인이 필요하다.

### 3.4 테스트 계획 관련

#### I. Integration test 범위 미구체

Task 파일의 "국내주식 preflight readiness integration test 추가 후 실행"과 "국내주식 reconciliation integration test 추가 후 실행"은 테스트 파일명과 테스트 시나리오가 구체적이지 않다.

**권장**: 예상 테스트 파일명과 최소 시나리오를 명시
- `tests/integration/test_kis_preflight_integration.py`: 장외시간 차단, 정상 readiness 반환
- `tests/integration/test_kis_reconciliation_integration.py`: drift 감지, pending skip, 불완전 snapshot skip

#### J. 기존 테스트 회귀 확인 범위

Task 파일의 "관련 API/백테스트 회귀 테스트 실행"이 너무 모호하다. 현재 6개의 integration test와 25개의 unit test가 있으므로, 최소한 `pytest tests/ -q`로 전체 실행을 명시하는 것이 좋다.

### 3.5 Configuration 관련

#### K. YAML 설정 확장 가능성에 대한 불확실성

PRD D-5에서 "반쪽 지원 금지"라는 원칙은 좋으나, Implementation Plan Step 4에서 "YAML에 추가한다면"이라는 조건부 표현이 있어서, 실제 구현 시점에 결정이 지연될 수 있다. 시장 시간 규칙(`09:00-15:30`)을 하드코딩할지 설정으로 뺄지 미리 결정해두는 것이 좋다.

**권장**: "KST 장시간 규칙은 Phase 5에서 코드 상수로 고정하며, YAML에 노출하지 않는다"처럼 확정

---

## 4. 구조/포맷 리뷰

| 항목 | 평가 | 비고 |
|------|------|------|
| PRD ↔ Implementation Plan 정합성 | 양호 | Epic A~E와 Step 0~6이 1:1 대응 |
| Implementation Plan ↔ Task 정합성 | 양호 | Phase 5-0~5-6이 Step 0~6과 대응 |
| Exit criteria 명확성 | 보통 | 일부 항목이 "테스트로 설명 가능하다" 같은 주관적 표현 |
| Impacted files 정확성 | 양호 | 실제 파일 경로와 대부분 일치, `app/settings.py` 포함됨 |
| Delivery slice 크기 | 양호 | 각 slice가 1-PR 크기에 적합 |
| Risk 식별 | 양호 | KIS API 스펙 불안정성, DTO-frontend 동시 수정 필요성 등 현실적 |

---

## 5. 종합 권장사항

| # | 항목 | 우선순위 |
|---|------|----------|
| 1 | `FillStatus` 확장 여부 확정 — `REJECTED` 추가 여부를 PRD에 명시 | 높음 |
| 2 | KIS API endpoint 매핑표 추가 — Implementation Plan에 사용할 KIS REST API path와 응답 필드 매핑 포함 | 높음 |
| 3 | receipt metadata 필드 목록 확정 — `KisOrderResult` 확장 범위 구체화 | 높음 |
| 4 | multi-sample timestamp semantics 확정 — 각 sample의 시간 처리 방법 명시 | 중간 |
| 5 | Dashboard DTO 확장 스펙 구체화 — 타입, nullable 여부, 기본값 | 중간 |
| 6 | Integration test 파일명/시나리오 구체화 — 추상적인 "추가 후 실행"을 구체 시나리오로 | 중간 |
| 7 | 시장시간 규칙의 구현 방식 확정 — 코드 상수 vs YAML 설정 | 중간 |
| 8 | skip event의 책임 분배 명시 — adapter vs loop 중 어디서 이벤트 생성할지 | 중간 |

---

## 6. 결론

전반적으로 **현재 코드베이스를 정확하게 반영한 잘 작성된 PRD**이다. 위 8가지 항목을 보강하면 구현 착수 시 설계 모호점 없이 진행할 수 있다.
