# Planning handoff checklist

Use this before handing plan output to build mode.

## Inputs

- User request
- `AGENTS.md` in-scope policies
- Repository facts from inspected files/commands

## Minimal evidence set

1. Task summary is concise and accurate.
2. Scope includes only smallest valid change set.
3. Confirmed vs Assumption vs Unknown are clearly separated.
4. Risks are concrete and testable.
5. Validation plan includes available build/lint/test/smoke commands.
6. Build handoff is implementation-ready without restating context.

## Risk prompts

- Could scope drift during implementation?
- Any compatibility/API or config contract impacts?
- Any deterministic behavior concerns for tests/backtests?

## Output prompt

- Is this plan directly usable by build mode?
- Are unknowns visible instead of hidden?
