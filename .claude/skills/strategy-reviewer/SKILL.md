---
name: strategy-reviewer
description: review trading logic, backtests, strategy code, execution flow, and risk enforcement in this repository. use when a change may alter pnl behavior, order sizing, state transitions, or operational safety.
---

# Strategy reviewer

Review changes with emphasis on correctness and trading risk.

## Review focus

1. Strategy correctness
2. Risk-limit enforcement
3. Execution and portfolio state transitions
4. Backtest realism and determinism
5. Missing tests or unsupported assumptions

## Review method

- Identify the decision point that changed.
- Trace its effect through risk, execution, and portfolio state.
- Look for sign errors, unit mismatches, stale state, and time-coupling.
- Check whether the tests would catch the failure mode.

## Output structure

### High-risk findings
Only issues that can change behavior incorrectly or unsafely.

### Medium-risk findings
Design or maintainability issues likely to cause later defects.

### Missing coverage
Tests or fixtures that should exist.

### Open questions
Only when evidence is incomplete.

See `references/review-heuristics.md` for the checklist.
