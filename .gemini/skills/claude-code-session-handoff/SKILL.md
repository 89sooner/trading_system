---
name: claude-code-session-handoff
description: help preserve context and resume work when claude code sessions grow large or hit usage limits. use when chatgpt needs to create a handoff plan, write or update a handoff.md file, recommend when to compact or clear context, explain how to resume a saved session, or convert a messy interrupted coding session into a clean continuation workflow for claude code.
---

# Claude Code Session Handoff

## Overview

Preserve task continuity across Claude Code limits, resets, and long-running sessions. Create a concrete handoff, choose the right context-management action, and recommend the safest resume path without losing progress or repeating failed approaches.

## Core workflow

1. Determine the interruption stage.
2. Preserve state in a handoff document before suggesting context resets.
3. Recommend the smallest command set needed to continue work.
4. Produce output that the user can paste directly into `HANDOFF.md` or into the next Claude Code session.

## Determine the current stage

Classify the request into one of these stages and respond accordingly.

### Stage 1: active work, low context pressure

Treat the session as normal work when the conversation is still focused and context pressure is low.

- 0-50%: continue working normally
- 50-75%: prepare for manual compaction
- around 70%: recommend proactive `/compact` instead of waiting for automatic compaction

### Stage 2: high context pressure, no hard stop yet

Treat the session as near handoff when the context window is crowded or the user says the session is becoming noisy.

- 75-90%: stop starting new subproblems
- begin writing `HANDOFF.md`
- preserve completed work, current branch, open questions, and next actions
- record failed approaches explicitly so the next session does not repeat them

### Stage 3: hard limit reached or immediate risk

Treat the session as interrupted when Claude Code reports a usage limit or the user expects a forced stop soon.

- write `HANDOFF.md` immediately
- name the session before clearing whenever possible
- clear only after the handoff is captured
- resume with the lightest viable path after reset

## Prioritize the handoff document

Always treat `HANDOFF.md` as the primary continuity artifact.

When creating or updating `HANDOFF.md`, include these sections in this order:

1. Goal
2. Current status
3. Completed work
4. Files changed or areas inspected
5. Decisions made
6. What worked
7. What didn't work
8. Open questions or risks
9. Exact next step
10. Resume commands

Make `What didn't work` mandatory whenever the user has already tried fixes, prompts, commands, or debugging paths. This section is critical because it prevents wasted tokens and repeated mistakes in the next session.

Keep the handoff concrete. Prefer exact file paths, branch names, commands, test names, and unresolved blockers over vague summaries.

If the user asks for a template, use the structure from `references/handoff-template.md`.

## Recommend context-management actions

Use this decision logic.

### Recommend `/compact`

Recommend `/compact` when the task is still the same, useful context still exists, and the user needs to reclaim space without losing the thread.

Prefer manual compaction before the session becomes critical. If the user gives no threshold, recommend manual `/compact` around 70% fullness.

When helpful, suggest focused compaction instructions such as:

- `/compact Focus on changed files, failing tests, and the next implementation step`
- `/compact Preserve attempted fixes, current blockers, and the final target behavior`

### Recommend `/clear`

Recommend `/clear` only when switching to unrelated work or after the user has already preserved the current task in `HANDOFF.md`.

Warn against clearing first. Clearing before writing a handoff destroys context that may be expensive to reconstruct.

### Recommend `/rename`

Recommend `/rename` before `/clear` or before pausing a session that may need to be resumed later. Prefer short task names such as `auth-refactor`, `payment-retry-bug`, or `szz-llm-compare`.

## Recommend resume paths

Prefer currently documented resume flows.

### Fastest path

Use `claude --continue` when the user wants the most recent conversation in the current directory.

### Named or selectable path

Use `claude --resume` to open the session picker.
Use `claude --resume <name-or-id>` when the user already knows the session name or session id.
Use `/resume` inside an active Claude Code session to switch to another conversation.

### Naming strategy

Encourage naming sessions early with either:

- `claude -n <session-name>` at startup
- `/rename <session-name>` during the session

If the user says `--resume [name]`, normalize it to the current documented form `claude --resume <name-or-id>`.

## Normalize outdated command wording

Claude Code command names and documentation can drift over time. If the user uses older wording, normalize it without making a big issue of it.

Apply these mappings when useful:

- `resume the last session` → `claude --continue`
- `resume by session name` → `claude --resume <name-or-id>`
- `switch sessions in the repl` → `/resume`
- `check usage` → prefer `/cost` for api-token cost details; mention `/stats` for subscriber usage patterns and `/status` for account or system status when relevant

If command availability may differ by installed version, tell the user to confirm with `/help` and `claude --version`.

## Mention optional automation carefully

Mention `claude-auto-resume` only as an optional third-party helper, not as the default solution.

When mentioning it:

- state that it is not an official Anthropic tool
- describe it as useful for long waits after usage limits
- warn that automation scripts may depend on Claude Code output formats and may use risky permission flags depending on implementation
- prefer official built-in resume flows first

## Output patterns

Choose the output format that matches the user's request.

### 1. Handoff document

Produce a ready-to-save `HANDOFF.md` using the template in `references/handoff-template.md`.

### 2. Recovery checklist

Produce a short ordered checklist for immediate recovery after an interruption.

Include, when relevant:

1. finalize `HANDOFF.md`
2. run `/rename <session-name>`
3. inspect `/cost`, `/stats`, or `/status` as appropriate
4. after reset, run `claude --continue` or `claude --resume <name-or-id>`
5. paste the exact next step from the handoff

### 3. Resume prompt

Produce a compact restart prompt that can be pasted into the resumed session.

The restart prompt must include:

- the goal
- what is already done
- what failed
- the next concrete action
- any constraints such as branch, files, tests, or environment assumptions

## Response style

Be direct and operational.
Do not give abstract productivity advice.
Prefer exact commands, thresholds, and document structure.
If the user provides partial notes, convert them into a clean handoff instead of asking to reorganize them manually.

## Resources

- For a copyable handoff structure, read `references/handoff-template.md`.
- For command notes and wording normalization, read `references/command-notes.md`.
