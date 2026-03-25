# Phase 3.5 Task Breakdown

## Epic A - Dashboard UX And Safe Controls
- [ ] Update the dashboard UI to use `pause`, `resume`, and `reset`
- [ ] Remove the stale `stop` button and any stop-oriented operator wording
- [ ] Show runtime status, heartbeat, positions, unrealized PnL, and recent events
- [ ] Add navigation entry points from existing frontend pages
- [ ] Add tests for invalid control transitions
- [ ] Add tests for idempotent control actions

## Epic B - Config And Operator Documentation
- [ ] Add `portfolio_risk` to `configs/base.yaml`
- [ ] Update `README.md` in English and Korean together
- [ ] Update `GEMINI.md`
- [ ] Update examples if config or operator workflow examples change

## Epic C - Live Constraint Cleanup
- [ ] Remove the generic single-symbol preflight restriction
- [ ] Preserve and document only broker-specific limitations if they still exist
- [ ] Add or update tests for live preflight behavior

## Epic D - Trade Analytics Edge Cases
- [ ] Add partial-fill tests
- [ ] Add scale-in tests
- [ ] Add scale-out tests
- [ ] Add flat-then-reopen tests
- [ ] Add empty-trade tests

## Epic E - Verification
- [ ] Run targeted frontend/API/runtime tests for touched areas
- [ ] Run broader regression tests
- [ ] Run the full test suite
- [ ] Run `ruff check src tests`
