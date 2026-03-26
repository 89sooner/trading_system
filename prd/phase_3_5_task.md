# Phase 3.5 Task Breakdown

## Epic A - Dashboard UX And Safe Controls

- [x] Update the dashboard UI to use `pause`, `resume`, and `reset`
- [x] Remove the stale `stop` button and any stop-oriented operator wording
- [x] Show runtime status, heartbeat, positions, unrealized PnL, and recent events
- [x] Add navigation entry points from existing frontend pages
- [x] Add tests for invalid control transitions
- [x] Add tests for idempotent control actions

## Epic B - Config And Operator Documentation

- [x] Add `portfolio_risk` to `configs/base.yaml`
- [x] Update `README.md` in English and Korean together
- [x] Update `GEMINI.md`
- [x] Update examples if config or operator workflow examples change

## Epic C - Live Constraint Cleanup

- [x] Remove the generic single-symbol preflight restriction
- [x] Preserve and document only broker-specific limitations if they still exist
- [x] Add or update tests for live preflight behavior

## Epic D - Trade Analytics Edge Cases

- [x] Add partial-fill tests
- [x] Add scale-in tests
- [x] Add scale-out tests
- [x] Add flat-then-reopen tests
- [x] Add empty-trade tests

## Epic E - Verification

- [x] Run targeted frontend/API/runtime tests for touched areas
- [x] Run broader regression tests
- [x] Run the full test suite
- [x] Run `ruff check src tests`
