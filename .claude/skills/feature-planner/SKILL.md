---
name: feature-planner
description: plan features, bug fixes, refactors, and architecture changes for this trading-system repository. use when a request needs a concrete execution plan, impacted modules, test scope, rollout notes, or risk analysis before coding.
---

# Feature planner

Turn an incoming request into a repository-specific implementation plan.

## Workflow

1. Restate the goal in repository terms.
2. Map the request onto the current package layout under `src/trading_system/`.
3. Identify the smallest set of modules, configs, docs, and tests that must change.
4. Call out trading-specific risks such as strategy drift, position-sizing errors, notional breaches, hidden state, or backtest/live mismatches.
5. Produce a plan using the output structure below.

## Output structure

Use this structure unless the user asked for another format.

### Goal
One concise paragraph.

### Assumptions
List only assumptions that materially affect the implementation.

### Impacted files
Group by package or concern.

### Implementation steps
Use ordered steps. Each step should describe what changes and why.

### Test plan
Cover unit tests first. Add integration or simulation tests only where they matter.

### Risks and follow-up
Mention failure modes, data-quality issues, and any deferred work.

## Repository guidance

- Keep strategy, risk, execution, portfolio, and analytics separated.
- Prefer extending explicit interfaces over adding cross-layer shortcuts.
- If the request changes configuration shape, include `configs/`, `examples/`, and `README.md` in the plan.
- If the request affects trading behavior, include at least one regression test idea.

See `references/planning-checklist.md` for the domain checklist.
