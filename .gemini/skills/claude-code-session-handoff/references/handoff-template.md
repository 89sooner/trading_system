# HANDOFF.md template

## Goal
- State the exact task to finish.

## Current status
- State what is true right now in 2-4 lines.

## Completed work
- List completed implementation, analysis, or debugging steps.

## Files changed or areas inspected
- List exact file paths, directories, logs, services, or commands already checked.

## Decisions made
- Record decisions that should not be revisited without a reason.

## What worked
- Record approaches that produced a useful result.

## What didn't work
- Record failed fixes, dead ends, rejected hypotheses, and misleading signals.
- Explain why each failed if known.
- Treat this section as mandatory once any debugging or experimentation has happened.

## Open questions or risks
- Record blockers, unknowns, assumptions, and anything the next session must verify.

## Exact next step
- Write the very next action as a concrete instruction.
- Good example: run `pytest tests/api/test_retry.py -k payment_timeout`, inspect `RetryPolicy.should_retry`, then patch backoff handling in `src/payments/retry.py`.

## Resume commands
- Most recent session: `claude --continue`
- Pick or resume by name: `claude --resume`
- Resume by name directly: `claude --resume <name-or-id>`
- Switch sessions inside Claude Code: `/resume`
