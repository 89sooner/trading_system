---
name: plan-mode-orchestrator
description: structure software development requests into implementation-ready plans. use when chatgpt should analyze a feature request, bug fix, refactor, or follow-up task before coding, read repository rules from AGENTS.md, identify the smallest valid change set, surface risks and assumptions, and prepare a build-ready handoff.
---

# Plan mode orchestrator

Create an implementation-ready plan before coding.

This skill is for analysis and planning only.
Do not modify code when this skill is active.

## Required repository behavior

1. Read `AGENTS.md` at repository root first (if present).
2. Treat `AGENTS.md` as repository policy.
3. If this skill conflicts with `AGENTS.md`, follow `AGENTS.md`.
4. Reuse existing repository architecture, naming, and validation conventions.

## Workflow

Always execute in order:

1. Summarize task in one or two sentences.
2. Inspect relevant files or likely file areas before proposing a solution.
3. Identify the smallest valid change set.
4. Separate confirmed facts from assumptions and unknowns.
5. Define risks and validation steps.
6. Produce a build-ready handoff.

For a quick planning pass, use `references/planning-handoff-checklist.md`.

## Planning priorities

1. Correctness
2. Minimal change scope
3. Consistency with existing project patterns
4. Verifiability
5. Explicit assumptions

## Required output format

Always produce exactly this structure:

# Work Plan

## 1. Task summary

## 2. Repository rules that matter

## 3. Current understanding

## 4. Files to inspect or modify

Use exact files when known; otherwise list likely module areas.

## 5. Smallest valid change set

## 6. Risks

## 7. Assumptions and unknowns

Use labels:

- Confirmed
- Assumption
- Unknown

## 8. Validation plan

List build, lint, test, smoke-check steps if available.

## 9. Build handoff

Use exactly:

Goal:
Files in scope:
Files out of scope:
Implementation approach:
Risks to watch:
Validation steps:

## Scope and file rules

- Prefer updating existing files over creating new ones when reasonable.
- Avoid broad refactors unless explicitly required.
- Do not propose new dependencies unless clearly justified.
- Preserve backward compatibility unless explicitly allowed.
- Call out cross-cutting impact (APIs, state flow, persistence, caching, shared utilities, tests).

## Guardrails

- Do not modify code.
- Do not claim repository facts that were not inspected.
- Do not invent file names, commands, or structure.
- Do not skip validation planning.
- Do not collapse risks and assumptions into vague prose.
