# Product Requirements Document (PRD) - Phase 3.5

## 1. Overview
Phase 3 delivered the core backend runtime needed for production-oriented trading operations. The system now includes authoritative live runtime state, emergency drawdown protection, multi-symbol orchestration on the unified execution path, trade analytics from fills, and live reconciliation support.

Phase 3.5 does not redefine those goals. It closes the remaining production-readiness gaps by aligning the frontend dashboard with the implemented runtime controls, synchronizing configuration and operator documentation, removing residual live-mode scaffolding constraints, expanding analytics edge-case coverage, and completing broader release validation.

## 2. Product Goals

### Goal 1. Operator-Safe Dashboard UX
The dashboard must accurately reflect the implemented runtime controls and provide a reliable operator surface for normal pause/resume flows and emergency reset flows.

### Goal 2. Config And Documentation Parity
The documented configuration and operator workflow must match the existing backend implementation, especially for `portfolio_risk`, dashboard control, and reconciliation behavior.

### Goal 3. Live-Mode Constraint Cleanup
Residual single-symbol live scaffolding must be removed where it is no longer justified, or explicitly documented when a broker-specific limitation still applies.

### Goal 4. Analytics Edge-Case Correctness
Trade extraction and trade statistics must be validated against complex fill sequences so reported analytics remain trustworthy.

### Goal 5. Broader Release Validation
The Phase 3 backend must be closed out with broader regression and full-suite validation rather than only the targeted tests already run during initial delivery.

## 3. Detailed Requirements

### 3.1 Dashboard Completion
- `frontend/dashboard.html` must reflect the actual runtime control contract: `pause`, `resume`, and `reset`.
- Stale `stop` semantics must be removed from the operator-facing dashboard workflow.
- The dashboard must show runtime state, heartbeat, positions, unrealized PnL, and recent events using the existing backend APIs.
- Existing frontend pages must provide navigation entry points to the dashboard where appropriate.
- UI expectations and API expectations must agree on idempotent and invalid transitions.
- `reset` must be documented as clearing `EMERGENCY` and returning the runtime to `PAUSED`, not directly to `RUNNING`.

### 3.2 Config And Operator Documentation Parity
- The `portfolio_risk` configuration surface already supported by app settings and backtest DTOs must be documented in config examples and operator docs.
- `configs/base.yaml`, `README.md`, `GEMINI.md`, and any affected examples must be updated together when the Phase 3.5 implementation changes configuration or operator workflow shape.
- Operator docs must cover dashboard control semantics, emergency reset behavior, and reconciliation cadence and skip/freeze behavior.

### 3.3 Live-Mode Constraint Cleanup
- Remaining single-symbol live scaffolding in `AppServices.preflight_live()` must be audited and removed when it is not required by a broker or provider integration.
- If a live multi-symbol limitation remains because of a specific broker integration, that limitation must be documented explicitly as temporary or integration-specific scope.
- Generic scaffold-era wording that incorrectly implies all live mode is single-symbol must be removed.

### 3.4 Analytics Correctness
- Trade extraction and trade-stat behavior must be validated for:
  - partial fills
  - scale-in sequences
  - scale-out sequences
  - flat-then-reopen flows
  - empty trade sets
- Phase 3.5 must preserve the existing dedicated analytics route:
  - `GET /api/v1/analytics/backtests/{run_id}/trades`
- Phase 3.5 must not merge trade analytics back into equity-curve summary responses.

### 3.5 Release Validation
- Validation must extend beyond the targeted Phase 3 suite.
- Dashboard control semantics, updated preflight behavior, analytics edge cases, and any doc/config-linked behavior changes must have corresponding verification.
- A full test-suite run is required before Phase 3.5 can be considered complete.

## 4. Non-Functional Requirements
- Preserve the unified execution path in `step.py`.
- Treat Phase 3.5 as additive hardening and completion work, not as an architecture reset.
- Keep public contracts stable:
  - `POST /api/v1/dashboard/control`
  - `pause`, `resume`, `reset`
  - `GET /api/v1/analytics/backtests/{run_id}/trades`
  - `portfolio_risk` as the documented config surface for drawdown, SL, and TP settings
- Maintain documentation parity across English and Korean sections in `README.md`.

## 5. Scope

### In Scope
- dashboard UX completion and operator-safe control handling
- config and documentation synchronization for existing Phase 3 behavior
- live preflight cleanup for remaining single-symbol scaffolding
- analytics edge-case test coverage
- broader regression and full-suite verification

### Out Of Scope
- redesigning Phase 3 runtime-state architecture
- redesigning reconciliation architecture
- changing the analytics route shape away from the dedicated backtest trade endpoint
- adding new trading strategies or new alpha logic

## 6. Success Criteria
- The dashboard UI matches backend runtime control semantics and no longer exposes stale stop behavior.
- Config examples and operator docs clearly show how to use `portfolio_risk`, dashboard control, and reconciliation behavior.
- Live preflight no longer blocks multi-symbol operation for non-broker reasons, or the remaining broker-specific limitation is explicitly documented.
- The analytics endpoint is covered by tests for partial fills, scale-in/out, flat-then-reopen, and empty-trade behavior.
- The full test suite is run before Phase 3.5 is closed.

## 7. Risks And Assumptions

### Assumptions
- Phase 3 backend implementation is the current baseline and should be extended rather than redesigned.
- The existing dashboard APIs and analytics route are stable enough to keep as the Phase 3.5 contract.

### Risks
- The dashboard can still mislead operators if UI state and runtime-state semantics diverge.
- Documentation can drift from real behavior if config examples and operator notes are not updated together.
- Hidden single-symbol assumptions may remain in live paths even after multi-symbol backend support shipped.
- Trade analytics can still be misleading if complex fill pairing is insufficiently covered by tests.
