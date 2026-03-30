---
name: python-implementer
description: implement or refactor python code in this repository. use when a task requires editing modules under src, tests, configs, or scripts, especially for strategy, risk, execution, portfolio, analytics, or backtest changes.
---

# Python implementer

Apply safe, repository-aligned Python changes.

## Workflow

1. Inspect the affected package and nearest interfaces before changing code.
2. Keep the change scoped to the requested behavior.
3. Add or update tests in the same change.
4. Run targeted validation when possible.
5. Report changed files, behavior impact, and residual risks.

## Implementation rules

- Prefer explicit dataclasses, protocols, and small modules.
- Avoid hidden global state.
- Keep side effects at boundaries such as providers, brokers, file I/O, and CLI entrypoints.
- Do not mix strategy logic with risk enforcement.
- Do not mix execution adapters with portfolio accounting.
- Preserve deterministic behavior in backtests.

## Validation

Run the smallest relevant check first.

- Unit-only logic: run targeted `pytest` for the affected package.
- Package-level change: run the nearest focused test file plus a smoke test if available.
- Config or docs-only change: verify examples and referenced paths.

## Output structure

### Changed files
### What changed
### Validation
### Risks

See `references/python-change-checklist.md` for a final review pass.
