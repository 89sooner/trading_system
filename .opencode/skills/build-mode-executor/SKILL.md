---
name: build-mode-executor
description: implement an approved development plan with tight scope control. use when chatgpt already has a clear goal, a defined change set, and validation steps, and should modify code while following AGENTS.md, preserving existing patterns, avoiding speculative refactors, and reporting exactly what changed and how it was verified.
---

# Build mode executor

Implement the approved plan with minimal, controlled changes.

## Required repository behavior

1. Read `AGENTS.md` at repository root first (if present).
2. Treat `AGENTS.md` as repository policy.
3. If this skill conflicts with `AGENTS.md`, follow `AGENTS.md`.
4. Follow existing repository structure, naming, tooling, and architecture patterns.

## Workflow

1. Restate the approved goal.
2. Inspect exact files in scope.
3. Implement the smallest valid change set.
4. Keep related logic in the appropriate layer.
5. Run relevant available validation steps.
6. Report exactly what changed, verification evidence, and remaining uncertainty.

For a quick final pass, use `references/build-execution-checklist.md`.

## Scope control rules

- Modify only files required by the approved plan.
- Keep changes minimal and focused.
- Do not add unrelated cleanup.
- Do not perform broad renames, file moves, or architecture rewrites unless explicitly required.
- Prefer extending existing patterns over new abstractions.
- Do not add dependencies unless clearly justified.

## Implementation rules

- Preserve backward compatibility unless explicitly allowed to break.
- Keep modules focused on one responsibility.
- Keep data structures explicit and predictable.
- Use semantic names.
- Preserve or add types for public/shared APIs where project patterns support them.
- Handle expected errors explicitly.
- Add comments only when explaining why a decision was made.

## Validation rules

Run available checks in this order when they exist:

1. build
2. lint
3. test
4. local smoke-check (if applicable)

If a step cannot run due to missing configuration, state it explicitly.
Do not claim success without evidence.

## Blocker handling

If safe implementation cannot continue:

1. stop scope expansion
2. state blocker clearly
3. state what is confirmed
4. state what remains unknown
5. request narrow return to plan mode

## Required final response format

Always end with this structure:

# Implementation Result

## 1. What changed

## 2. Files modified

## 3. Verification

List each command run and result. If something could not run, state why.

## 4. Remaining limitations or follow-up work

## Guardrails

- Do not silently expand scope.
- Do not fabricate build/lint/test success.
- Do not ignore validation failures.
- Do not replace core tooling casually.
- Do not introduce secrets or private configuration.
- Do not rewrite large project areas without explicit instruction.
