# Phase 3.5 Implementation Plan

## Goal
Finish the remaining Phase 3 work needed for production-facing completeness without redesigning the backend delivered in Phase 3. Phase 3.5 closes the dashboard/operator gap, synchronizes docs and configuration with existing behavior, removes leftover live-mode scaffolding restrictions, expands trade-analytics edge-case coverage, and completes broader verification.

## Assumptions
- The current Phase 3 backend implementation is the base and should not be redesigned.
- `src/trading_system/execution/step.py` remains the unified execution path for behavior that affects trading outcomes.
- `portfolio_risk` already exists in app settings and backtest DTOs and should remain the documented configuration surface.
- The dedicated analytics route remains:
  - `GET /api/v1/analytics/backtests/{run_id}/trades`
- Phase 3.5 is additive follow-up work and does not reopen runtime-state, reconciliation, or analytics-route architecture.

## Impacted Areas
- `frontend/dashboard.html`
- `frontend/index.html`
- frontend page JavaScript referenced by the dashboard and existing navigation flows
- `configs/base.yaml`
- `README.md`
- `GEMINI.md`
- `src/trading_system/app/services.py`
- analytics and live-preflight related tests under `tests/`

## Implementation Steps

1. Harden dashboard control semantics.
Align the dashboard with the implemented control contract by using `pause`, `resume`, and `reset` only. Remove stale `stop` semantics from the UI-facing operator workflow. Define disabled or error behavior for invalid transitions and add route-level tests for invalid and idempotent actions.

2. Complete dashboard UX and navigation.
Ensure the dashboard renders runtime state, heartbeat, unrealized PnL, and recent events from the existing APIs. Add navigation entry points from the existing frontend pages so operators can reach the dashboard without manual URL entry.

3. Sync config and operator docs.
Add a `portfolio_risk` section to `configs/base.yaml`. Update `README.md` and `GEMINI.md` together so the documented operator workflow matches the implemented dashboard control and reconciliation behavior. Update examples if Phase 3.5 changes how configuration or operator flows are presented.

4. Remove non-essential single-symbol live restrictions.
Refactor `preflight_live()` so generic live-mode preflight no longer depends on `_single_symbol()` unless a concrete broker/provider limitation requires it. If a broker-specific limitation still exists, isolate it to that integration path and document it explicitly rather than preserving scaffold-era generic restrictions. Update affected unit tests.

5. Expand analytics edge-case coverage.
Add tests for partial fills, scale-in, scale-out, flat-then-reopen, and empty-trade scenarios. Keep trade DTOs and the dedicated analytics endpoint stable while increasing behavioral coverage.

6. Run broader verification.
Run targeted tests for touched dashboard, runtime, preflight, and analytics areas first. Then run a broader regression suite. Run the full test suite last before considering Phase 3.5 complete.

## Epic Breakdown

### Epic A. Dashboard UX And Safe Controls
- Update the dashboard UI to `pause`, `resume`, and `reset`.
- Remove the stale `stop` button and operator wording.
- Render status, heartbeat, positions, unrealized PnL, and recent events using the current backend routes.
- Add navigation entry points from the existing frontend pages.
- Add invalid-transition and idempotent-control tests.

### Epic B. Config And Operator Documentation
- Add `portfolio_risk` to `configs/base.yaml`.
- Update `README.md` in English and Korean together.
- Update `GEMINI.md`.
- Update examples if config shape or operator workflow examples change.

### Epic C. Live Constraint Cleanup
- Remove generic single-symbol preflight restrictions.
- Preserve only broker-specific limitations that still materially exist.
- Document any remaining integration-specific limitations.
- Update preflight-related tests.

### Epic D. Trade Analytics Edge Cases
- Add edge-case trade-stat coverage for partial fills, scale-in, scale-out, flat-then-reopen, and empty trade sequences.
- Keep the dedicated analytics API stable.

### Epic E. Verification
- Run targeted frontend/API/runtime tests for touched areas.
- Run broader regression tests after behavior changes.
- Run the full test suite.
- Run `ruff check src tests`.

## Test Plan

### Unit Tests
- Dashboard route tests for invalid and idempotent `pause`/`resume`/`reset` flows.
- Live preflight tests covering the removal of generic single-symbol restrictions.
- Trade analytics tests for partial fills, scale-in, scale-out, reopen, and empty trade sequences.

### Integration And Manual Verification
- Manual dashboard smoke check for rendering, polling, and control behavior.
- Integration or route-level verification that dashboard control semantics remain aligned with the runtime.
- Broader regression run after Phase 3.5 code changes.
- Full test-suite run before completion.

## Risks And Follow-Up
- If dashboard control semantics remain inconsistent between UI and backend, operators can take the wrong action during incident response.
- If docs and config examples are updated partially, the repo will continue to misrepresent Phase 3 behavior.
- If a broker-specific live limitation is left generic, it will hide real multi-symbol capability in the rest of the stack.
- If analytics edge cases are not covered, reported trade metrics can still be wrong around realistic fill sequences.
