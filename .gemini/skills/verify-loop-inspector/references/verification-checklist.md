# Verification checklist

Use this checklist after implementation and before declaring completion.

## Inputs

- Approved plan or explicit target from the user
- `AGENTS.md` policies in scope
- Actual changed files (`git diff`, `git show`, or latest commit)

## Minimal evidence set

1. Confirm target statement in one sentence.
2. Confirm inspected files/modules are listed.
3. Run focused tests first.
4. Run broader checks only when surface area warrants it.
5. Capture pass/fail/blocked for each command.

## Comparison prompts

- Goal: Does behavior match intended outcome?
- Scope: Any unrelated edits or drift?
- Rules: Any AGENTS.md policy violations?
- Compatibility: Any likely break in CLI/config/tests/docs contract?
- Risks: Any unknowns left unverified?

## Decision prompts

- **Pass** if all critical checks are evidenced and clean.
- **Needs fix** if concrete defects remain and can be fixed in the same scope.
- **Needs re-plan** if defects imply new scope or unresolved architecture questions.
