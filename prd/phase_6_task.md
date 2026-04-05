# Phase 6 Task Breakdown

## Usage

- 이 파일은 Phase 6 구현 진행 상황과 검증 증적을 기록한다.
- 체크박스는 실제 구현 작업과 검증 기준을 뜻한다.
- 각 slice가 끝날 때 `Execution Log`를 갱신한다.
- PRD 수준 범위는 `phase_6_prd.md`를 기준으로 한다.
- 상세 설계와 순서는 `phase_6_implementation_plan.md`를 기준으로 한다.
- 이 문서는 backlog promotion과 document hygiene를 반영한 Phase 6 실행 기록이다.

## Status Note

- 이 문서는 `prd/phase_6_prd.md`의 실행 추적 기록이다.
- 현재 체크박스는 Phase 6 구현 및 검증 결과를 반영한다.
- historical task status는 `prd/phase_3_task.md`, `prd/phase_4_task.md`, `prd/phase_5_task.md`의 status note와 함께 해석한다.

## Phase 6-0. Backlog And Status Alignment

- [x] `phase_5_task.md`의 follow-up 4개가 Phase 6 범위로 승격되었음을 문서 간 cross-link로 고정
- [x] `phase_3_task.md`, `phase_4_task.md`, `phase_5_task.md`의 status note가 active backlog와 historical/manual-pending 범위를 혼동하지 않도록 유지
- [x] README roadmap과 Phase 6 문서가 동일한 backlog 표현을 사용하도록 동기화
- [x] Phase 6 구현 범위 밖 항목(신규 자산군, 신규 브로커, async order-state machine 등)을 다시 확인

Exit criteria:
- Phase 6 backlog source가 `phase_6_prd.md`와 `phase_6_task.md`로 명확히 고정된다.

## Phase 6-1. Multi-Symbol Preflight Contract

- [x] `/api/v1/live/preflight`의 multi-symbol 처리 목표를 구현/문서 기준으로 확정
- [x] 첫 심볼만 처리하는 현재 제한을 제거할지, 명시적 제약으로 유지할지 결정
- [x] readiness 결과를 심볼별로 설명할 DTO/schema contract를 정의
- [x] 기존 preflight consumer와의 backward compatibility 기준을 명시
- [x] 관련 API route/schema/unit/integration test 범위를 식별

Exit criteria:
- multi-symbol preflight 처리 범위가 API contract와 operator-facing docs에서 일치한다.

## Phase 6-2. Pending Order Detection Hardening

- [x] `pending_symbols`의 authoritative source를 재검토
- [x] KIS 전용 unresolved/open-order source 사용 가능 범위를 문서화
- [x] `hldg_qty != ord_psbl_qty` 휴리스틱을 대체, 축소, 또는 fallback으로 한정하는 규칙 명시
- [x] fallback 사용 시 fail-closed/reconciliation skip 규칙을 테스트 가능한 형태로 고정
- [x] adapter/reconciliation regression test 범위를 정의

Exit criteria:
- pending order detection source와 fallback 정책이 문서/테스트 기준으로 설명 가능하다.

## Phase 6-3. Configuration Parity Recovery

- [x] `TRADING_SYSTEM_RECONCILIATION_INTERVAL`의 YAML loader support 여부를 확정
- [x] `portfolio_risk`를 `config.settings.load_settings()` 경로에 통합할지 고정
- [x] YAML 설정을 지원하는 경우 `src/trading_system/config/settings.py`, `configs/`, `examples/`, `README.md`, 관련 테스트를 같은 변경에 포함
- [x] env-var override와 YAML 기본값의 precedence를 문서에 명시
- [x] commented example이 아니라 active typed config로 동작하는지 검증 계획 수립

Exit criteria:
- reconciliation interval과 `portfolio_risk`의 설정 경로가 loader/docs/tests에서 일관된다.

## Phase 6-4. Final Doc Sync And Closure Criteria

- [x] README, 관련 runbook, examples가 최종 설정/운영 제약을 동일하게 설명
- [x] historical task 문서와 active Phase 6 문서의 역할 차이를 다시 점검
- [x] execution log, validation evidence, residual risks를 실제 결과로 채울 준비 완료
- [x] Phase 6 종료 기준과 잔여 후속 범위를 문서상 확정

Exit criteria:
- 문서만 읽고 현재 활성 backlog, 설정 경로, 운영 제약을 혼동 없이 설명할 수 있다.

## Verification Checklist

### Required unit tests

- [x] `pytest tests/unit/test_config_settings.py -q`
- [x] `pytest tests/unit/test_execution_adapters_and_broker.py -q`
- [x] `pytest tests/unit/test_reconciliation.py -q`
- [x] `/api/v1/live/preflight` multi-symbol contract 관련 unit test 추가 후 실행

### Required integration tests

- [x] `pytest tests/integration/test_config_loader_integration.py -q`
- [x] multi-symbol preflight integration test 추가 후 실행
- [x] reconciliation pending-order detection integration test 추가 후 실행

### Broader regression

- [x] 관련 API/config/live loop 회귀 테스트 실행
- [x] touched area 통과 후 broader regression 실행

### Manual verification

- [x] operator-facing docs와 README가 동일한 설정 제약을 설명하는지 확인
- [x] multi-symbol preflight 요청/응답 예시가 문서와 실제 contract에 맞는지 확인
- [x] YAML 설정과 env-var override precedence가 운영자 관점에서 이해 가능한지 확인

## Execution Log

### Date
- 2026-03-31

### Owner
- ChatGPT (Phase 6 Step 1 implementation)

### Slice completed
- Step 1 / Phase 6-1. Multi-Symbol Preflight Contract
- Step 2 / Phase 6-2. Pending Order Detection Hardening
- Step 3 / Phase 6-3. Configuration Parity Recovery
- Step 4 / Phase 6-4. Final Doc Sync And Closure Prep

### Scope implemented
- `/api/v1/live/preflight` route-level single-symbol restriction removed
- `PreflightCheckResult` extended with `quote_summaries` and `symbol_count`
- KIS live preflight now checks all requested symbols instead of only `symbols[0]`
- Backward compatibility preserved via primary `quote_summary` field
- README live preflight contract updated for multi-symbol detail fields
- KIS balance parsing no longer assumes missing `ord_psbl_qty` means "no pending order"
- Pending-order detection now requires explicit broker-provided `ord_psbl_qty` for held symbols
- Missing pending-order signal now fails closed via snapshot rejection, causing reconciliation skip
- KIS runbook updated to describe balance-signal dependency and fail-closed behavior
- YAML loader now parses `app.reconciliation_interval`
- YAML loader now parses typed `portfolio_risk` settings
- `configs/base.yaml` and `examples/sample_live_kis.yaml` now include active parity fields
- README now documents YAML parsing support plus env-var precedence for reconciliation interval
- Runbooks and architecture docs now reflect multi-symbol preflight support, KIS snapshot-backed reconciliation, and current fail-closed pending-order behavior
- README roadmap now records Phase 6 hardening/parity as delivered instead of draft backlog

### Files changed
- `src/trading_system/app/services.py`
- `src/trading_system/api/routes/backtest.py`
- `src/trading_system/api/schemas.py`
- `src/trading_system/config/settings.py`
- `src/trading_system/config/__init__.py`
- `src/trading_system/integrations/kis.py`
- `configs/base.yaml`
- `examples/sample_live_kis.yaml`
- `tests/unit/test_app_services.py`
- `tests/unit/test_api_server.py`
- `tests/unit/test_api_backtest_schema.py`
- `tests/unit/test_config_settings.py`
- `tests/unit/test_kis_integration.py`
- `tests/integration/test_config_loader_integration.py`
- `tests/integration/test_kis_preflight_integration.py`
- `docs/runbooks/kis-domestic-live-operations.md`
- `docs/runbooks/kis-domestic-live-operations.ko.md`
- `docs/runbooks/release-gate-checklist.md`
- `docs/runbooks/release-gate-checklist.ko.md`
- `docs/runbooks/incident-response.md`
- `docs/runbooks/incident-response.ko.md`
- `docs/architecture/user-use-cases.md`
- `docs/architecture/user-use-cases.ko.md`
- `docs/architecture/workspace-analysis.md`
- `docs/architecture/workspace-analysis.ko.md`
- `README.md`

### Commands run
- `uv run --python .venv/bin/python --no-sync pytest tests/unit/test_app_services.py tests/unit/test_api_server.py tests/unit/test_api_backtest_schema.py tests/integration/test_kis_preflight_integration.py -q` → 26 passed
- `uv run --python .venv/bin/python --no-sync pytest tests/unit/test_app_services.py tests/unit/test_api_server.py tests/unit/test_api_backtest_schema.py tests/integration/test_kis_preflight_integration.py -q` → 27 passed (after primary `quote_summary` edge-case fix)
- `uv run --python .venv/bin/python --no-sync pytest tests/unit/test_kis_integration.py tests/unit/test_reconciliation.py tests/integration/test_kis_reconciliation_integration.py -q` → 26 passed
- `uv run --python .venv/bin/python --no-sync pytest tests/unit/test_config_settings.py tests/integration/test_config_loader_integration.py -q` → 13 passed
- `uv run --python .venv/bin/python --no-sync pytest tests/unit/test_app_services.py tests/unit/test_api_server.py tests/unit/test_api_backtest_schema.py tests/integration/test_kis_preflight_integration.py tests/unit/test_kis_integration.py tests/unit/test_reconciliation.py tests/integration/test_kis_reconciliation_integration.py tests/unit/test_config_settings.py tests/integration/test_config_loader_integration.py tests/unit/test_execution_adapters_and_broker.py -q` → 71 passed

### Validation results
- Targeted Step 1 unit/integration tests passed (26 passed)
- Multi-symbol live preflight contract now returns `quote_summaries` and `symbol_count`
- Existing `quote_summary` field remains present for backward compatibility
- Primary `quote_summary` now stays tied to the first requested symbol instead of the first successful quote
- Targeted Step 2 unit/integration tests passed (26 passed)
- Pending-order detection now fails closed when broker balance data lacks `ord_psbl_qty` for a held symbol
- Reconciliation skip/frozen-cash behavior remains unchanged once `pending_symbols` is present
- Targeted Step 3 unit/integration tests passed (13 passed)
- YAML loader parity now covers both `app.reconciliation_interval` and `portfolio_risk`
- `portfolio_risk.max_daily_drawdown_pct` loader validation now matches runtime rule (`< 1`)
- Broader Phase 6 regression suite passed (71 passed)
- Operator-facing docs, architecture docs, and README now agree on multi-symbol preflight, reconciliation signal handling, and YAML parity behavior
- README roadmap now reflects Phase 6 as delivered rather than draft backlog

### Risks / follow-up
- `src/trading_system/api/routes/backtest.py` has pre-existing Pyright diagnostics unrelated to Step 1 changes
- `src/trading_system/integrations/kis.py` has a pre-existing Pyright diagnostic on transport return coverage unrelated to Step 2 behavior
- test-file LSP import warnings for config tests appear environment-specific; runtime pytest validation passed
- KIS pending-order authority still depends on balance-snapshot `ord_psbl_qty` rather than a dedicated unresolved/open-order API
- Legacy preflight consumers may still need migration from `quote_summary`-only parsing to `quote_summaries`/`symbol_count`
