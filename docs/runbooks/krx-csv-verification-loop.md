# KRX CSV feature verification loop (2026-03-17)

## Problem 1-Pager

### Context
- The implemented feature added CSV-backed backtests for KRX-style symbols (for example `005930`) through app settings and service wiring.
- The prior verification loop identified two evidence gaps: (1) explicit approved target traceability and (2) command-level runtime validation evidence.

### Problem
- The repository had code and tests for the feature, but no explicit verification artifact tying the approved target to concrete validation outputs.

### Goal
- Record a minimal, durable verification artifact that maps target → implementation scope → executed validation evidence.

### Non-Goals
- No trading logic changes.
- No configuration schema changes.
- No refactor of runtime modules.

### Constraints
- Keep this loop small and safe.
- Use existing tests and avoid new dependencies.
- Preserve deterministic behavior.

## Approved target reference
- Explicit target used for this loop: feature commit `411b0ca` (`Add CSV backtest provider path for KRX symbols`) and its scoped files.

## Option comparison (before deciding)
- Option A: Leave evidence only in ephemeral CI/local logs.
  - Pros: zero repository diff.
  - Cons: poor auditability; future loops cannot cite durable proof.
  - Risks: recurring verification gaps.
- Option B: Add a small runbook verification note in-repo.
  - Pros: durable, reviewable traceability in one file.
  - Cons: one additional docs file to maintain.
  - Risks: minor documentation staleness over time.

**Chosen:** Option B (simplest durable path).

## Scope inspected
- `src/trading_system/app/settings.py`
- `src/trading_system/app/services.py`
- `src/trading_system/app/main.py`
- `src/trading_system/data/provider.py`
- `tests/unit/test_app_services.py`
- `tests/unit/test_app_main.py`
- `README.md`
- `configs/krx_csv.yaml`
- `examples/sample_backtest_krx.yaml`

## Validation evidence
- `pytest tests/unit/test_app_services.py -q` → pass (`2 passed`)
- `pytest tests/unit/test_app_main.py -q` → pass (`6 passed`)
- `pytest -m smoke -q` → pass (`2 passed, 44 deselected`)

## Impact note
- No production code changed in this loop; only verification documentation was added.
- Runtime behavior remains unchanged, and risk is limited to documentation drift.

## Decision
- Pass

## Remaining risks / unknowns
- This artifact references a commit-level approved target; if your process requires issue/ADR-level approval linkage, add that ID in a future docs-only follow-up.

## Immediate next actions
1. Link this verification note to a formal issue or ADR ID for auditability.
2. Capture CI job URL or artifact path for the three test commands in the next loop report.
3. Keep this runbook docs-only unless runtime behavior changes.

## Next loop handoff
Goal:
- Strengthen approval traceability from commit-level to issue/ADR-level linkage.

Why another loop is needed:
- Current verification passes technically, but governance traceability is still noted as a remaining unknown.

Files likely in scope:
- `docs/runbooks/krx-csv-verification-loop.md`
- `README.md` (only if discovery links need updates)
- issue/ADR metadata location used by the team

Known issues:
- Approved target is linked to commit `411b0ca`, not yet to issue/ADR ID.

Validation to rerun:
- `pytest tests/unit/test_app_services.py -q`
- `pytest tests/unit/test_app_main.py -q`
- `pytest -m smoke -q`
