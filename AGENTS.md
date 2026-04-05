# AGENTS.md

This repository is a Python trading-system workspace.

## Working defaults

- Use Python 3.12.
- Keep application code under `src/trading_system/`.
- Keep tests under `tests/`.
- Prefer small, explicit modules over large utility files.
- Preserve deterministic behavior in backtest code. Any time-dependent logic must be injected or configurable.
- Treat strategy, risk, execution, and analytics as separate layers. Do not couple them directly when an interface will do.
- Maintain a unified execution path (`step.py`) across backtesting and live environments to ensure behavioral parity.
- When changing trading logic, update or add tests in the same change.
- When changing configuration shape, update `configs/`, `examples/`, and `README.md` together.

## Expected workflow

1. Read the nearest `AGENTS.md` if one exists.
2. Inspect the impacted package before editing.
3. Make the smallest coherent change that satisfies the task.
4. Run targeted tests first, then broader checks if the surface area is large.
5. Summarize changed files, risks, and follow-up work.

## Code style

- Prefer dataclasses, typed protocols, and small service objects.
- Keep side effects at boundaries such as providers, brokers, and file I/O.
- Avoid hidden state in strategy logic.
- Prefer composition over inheritance except for clearly defined base interfaces.
- Do not introduce new dependencies unless they clearly reduce complexity.

## Testing expectations

- Unit tests for risk rules, sizing, metrics, and strategy signal logic.
- Integration tests for order flow, broker adapters, and backtest orchestration when those layers are added.
- For bug fixes, add a regression test that fails before the fix and passes after it.

## Skills in this repo

Use repository skills from the local runtime skill directories such as `.claude/skills/`, `.codex/skills/`, `.gemini/skills/`, and `.opencode/skills/` when those directories are present and the task matches their purpose.

- `feature-planner`: turn a request into a concrete implementation plan.
- `python-implementer`: implement or refactor Python code safely.
- `strategy-reviewer`: review strategy, backtest, and risk changes.
- `docs-maintainer`: update documentation, examples, and operator notes.
- `verify-loop-inspector`: verify implementation against approved plan, validation evidence, and repository policy, then decide pass/fix/re-plan with next-loop handoff.
- `build-mode-executor`: implement approved plans with strict scope control, run validation in build/lint/test/smoke priority, and report exact implementation evidence.
- `plan-mode-orchestrator`: structure requests into implementation-ready plans with explicit scope, risks, assumptions, and build handoff.
- `frontend-product-designer`: design and implement production-grade React/Next.js frontends with stronger structure, accessibility, responsive behavior, and verification loops.
- `phase-planner`: create a new phase PRD, implementation plan, and task tracking document set under `prd/`.
- `claude-code-session-handoff`: preserve context across long Claude Code sessions by creating a concrete handoff and resume path.

## CLI and repository efficiency defaults

- Prefer `rg` (ripgrep) over `grep` for text search.
- Prefer `fd` over `find` for simple file discovery when available.
- Prefer `jq` for JSON inspection instead of dumping raw JSON with `cat`.
- Prefer `git grep` when searching only tracked files.
- Prefer targeted reads such as `sed`, `head`, and `tail` over full-file `cat`.
- Before using legacy commands such as `grep` or `find`, first check whether `rg`, `fd`, and `jq` are available and use them by default.
- Always minimize command output size to improve speed and reduce token usage.
- Read narrowly first, then expand only if needed.

## Required tool bootstrap

If the following tools are missing, install them before doing broad repository analysis:

- `rg` / `ripgrep`
- `fd` or `fdfind`
- `jq`

Tool availability checks:

```bash
command -v rg
command -v fd || command -v fdfind
command -v jq
```
