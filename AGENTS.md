# AGENTS.md - Project Working Instructions

## Purpose

This file defines how agents should work in this repository.
Agents must prioritize correctness, maintainability, and consistency with existing project patterns.

## High-Level Rules

- Read the current repository structure before making changes.
- Follow existing conventions unless there is a strong reason not to.
- Prefer minimal, focused changes over broad refactors.
- Do not add features that were not requested.
- Do not introduce new dependencies unless clearly justified.
- Keep implementation verifiable with available build, lint, and test steps.
- Explain assumptions explicitly when repository state is incomplete or unclear.

## Repository Awareness

Before making changes, inspect:

- project structure
- package manager and scripts
- framework/runtime/tooling already in use
- shared utilities, components, modules, or internal abstractions
- linting, formatting, and test setup
- existing architectural patterns

Prefer updating existing files over creating new ones when reasonable.

## Planning Rules

Before implementation:

1. summarize the task
2. inspect the relevant files
3. identify the smallest valid change set
4. list files to create or modify
5. identify risks, assumptions, and validation steps

Do not start coding until the approach is clear.

## Implementation Rules

- Keep components/modules focused on one responsibility.
- Avoid mixing UI, state logic, and persistence logic excessively.
- Extract repeated logic into reusable utilities or helpers.
- Keep data structures explicit and predictable.
- Use semantic naming.
- Avoid hardcoded values unless trivial and justified.
- Preserve backward compatibility unless the task explicitly allows breaking changes.

## Code Quality Rules

- Use the project’s existing language and style conventions.
- Favor readable code over clever code.
- Keep functions reasonably short.
- Add types for public APIs, shared data shapes, and exported functions.
- Avoid weak typing where the project supports stronger typing.
- Handle expected errors explicitly.
- Write comments only when they explain why a decision was made.

## Validation Rules

After implementation, run the relevant available commands.
Typical priority:

1. build
2. lint
3. test
4. local smoke-check if applicable

If any validation step cannot run because configuration is missing, say so clearly.
Do not claim success without verification.

- Run the relevant available commands after implementation.
- If a command fails because a tool is unavailable or missing in the environment, do not force that tool.
- Use a compatible alternative that already works in the current environment.
- If the fallback changes the validation process, mention it clearly in the final response.

## Response Rules

In the final response, always include:

1. what changed
2. which files were modified
3. how the result was verified
4. remaining limitations, assumptions, or follow-up work

## Tool Fallback Rules

- If a command fails because a required tool is unavailable, missing, or not installed in the current environment, do not force that tool.
- Use a compatible alternative that already works in the environment.
- Example: if `uv` fails with an ENOENT error such as `no such file or directory` or `posix_spawn 'uv'`, use another available Python workflow instead.
- Mention the fallback in the final response only if it affected implementation, validation, or reproducibility.

## Prohibited Actions

- Do not rewrite large areas of the project without explicit instruction.
- Do not replace core tooling casually.
- Do not add secrets, tokens, or private configuration into the codebase.
- Do not fabricate test/build success.
- Do not silently ignore failing validation.

## Project-Specific Section

Replace this section with repository-specific rules such as:

- framework choice
- folder structure
- naming rules
- API conventions
- UI standards
- accessibility requirements
- state management rules
- persistence rules
- deployment constraints

## Agent Loop Rules

Work in a repeated loop of:

1. plan
2. build
3. verify
4. plan again if needed

### Loop behavior

- Always read this `AGENTS.md` first before applying any skill-specific workflow.
- If repository rules in `AGENTS.md` conflict with a skill's instructions, follow `AGENTS.md`.
- In plan mode, do not modify code. Produce a clear implementation plan first.
- In build mode, implement only the approved plan and keep the change set minimal.
- In verify mode, validate the result against the plan and repository rules, then prepare the next loop input if more work is needed.
