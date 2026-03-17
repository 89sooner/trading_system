---
name: verify-loop-inspector
description: verify implemented changes against the approved plan and repository rules. use when chatgpt should inspect what changed, run available validation steps, compare the result with AGENTS.md and the plan, separate verified facts from unknowns, and produce a concise next-loop handoff for another planning cycle if needed.
---

# Verify loop inspector

Verify post-implementation results and decide the next loop step.

## Required repository behavior

1. Read `AGENTS.md` at repository root first (if present).
2. Treat `AGENTS.md` as repository policy.
3. If this skill conflicts with `AGENTS.md`, follow `AGENTS.md`.
4. Compare the result against both the approved plan and repository rules.

## Workflow

1. Restate the target that was supposed to be achieved.
2. Inspect changed files and current implementation state.
3. Run relevant available validation steps.
4. Compare outcomes against the approved plan and `AGENTS.md`.
5. Separate verified facts, failures, and unknowns.
6. Decide the next loop action.
7. Produce compact handoff if another loop is needed.

For quick completion checks, use `references/verification-checklist.md`.

## Verification priorities

Check in this order:

1. Implementation matches approved goal.
2. Implementation stayed within approved scope.
3. Available validation passed.
4. Project conventions and compatibility preserved.
5. No unresolved regression risk remains.

## Required output format

Always produce exactly this structure:

# Verification Result

## 1. Target checked

## 2. What was inspected

## 3. Validation evidence

List each command run and result. If something could not run, state why.

## 4. Decision

Choose exactly one:

- Pass
- Needs fix
- Needs re-plan

## 5. Findings

## 6. Scope compliance

## 7. Remaining risks or unknowns

## 8. Next loop handoff

If more work is needed, use exactly:

Goal:
Why another loop is needed:
Files likely in scope:
Known issues:
Validation to rerun:

If complete, write:

No further loop required.

## Decision rules

### Pass
Use only when target is met, scope is respected, relevant validation passed (or explicitly N/A), and no material unresolved issue remains.

### Needs fix
Use when goal is mostly correct but specific issues remain, validation failed, or minor scope drift can be corrected without re-planning.

### Needs re-plan
Use when structural gaps, critical unknowns, or material scope changes require a new planning cycle.

## Guardrails

- Prefer evidence over intuition.
- Do not mark unverified behavior as verified.
- Do not hide failed checks with vague wording.
- Do not start coding in this verification mode.
