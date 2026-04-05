---
name: phase-planner
description: create a new phase PRD, implementation plan, and task tracking document set when a new feature or improvement cycle is requested. use when the user wants to start a new phase in the prd/ directory with structured planning documents.
---

# Phase planner

Turn a feature request or improvement goal into a complete phase document set under `prd/`.

## Trigger

Use this skill when:
- The user requests a new feature, improvement cycle, or phase
- The user says "new phase", "phase plan", "phase-planner", or similar
- A significant body of work needs structured PRD + implementation plan + task tracking

## Workflow

### Step 1. Detect next phase number

1. Scan `prd/` for existing `phase_*_prd.md` files.
2. Determine the highest phase number (treat `3_5` as `3.5`, etc.).
3. Set the next phase number as `N+1` (integer). If the user specifies a number, use that.

### Step 2. Analyze context

1. Read the most recent `phase_*_prd.md` to understand the current baseline.
2. Read the most recent `phase_*_task.md` to check for open follow-ups or residual risks.
3. Identify what carries forward vs. what is new scope.

### Step 3. Create PRD (`phase_{N}_prd.md`)

Write the PRD following the structure in `references/prd-template.md`. Key rules:
- Start with cross-reference links to the previous phase and sibling documents.
- State the document purpose clearly.
- Define Goal, Current Baseline, Non-Goals, Hard Decisions.
- Break scope into Epics with explicit include/exclude boundaries.
- List Impacted Files grouped by concern.
- Define Delivery Slices for incremental progress.
- End with Success Metrics and Risks/Follow-up.
- Write in Korean following the established convention of this repository.

### Step 4. Create Implementation Plan (`phase_{N}_implementation_plan.md`)

Write the plan following `references/implementation-plan-template.md`. Key rules:
- Restate the goal with core implementation principles.
- Lock Preconditions and Design Decisions before listing steps.
- Define Contract Deltas for each affected subsystem.
- Sequence steps with: purpose, files, concrete work items, exit criteria.
- Include a Validation Matrix (unit tests, integration tests, manual verification).
- Recommend PR slices aligned to implementation steps.
- End with Risks and Fallbacks with concrete mitigations.

### Step 5. Create Task Breakdown (`phase_{N}_task.md`)

Write the task doc following `references/task-template.md`. Key rules:
- Start with Usage section explaining how this file is used.
- Add a Status Note marking all items as active backlog (not yet implemented).
- Create one section per implementation step with `- [ ]` checkboxes.
- Each section must have explicit Exit Criteria.
- Include a Verification Checklist (unit tests, integration tests, broader regression, manual verification).
- Include an empty Execution Log section ready to be filled during implementation.
- All checkboxes start unchecked.

### Step 6. Validate cross-references

- Ensure all three documents reference each other correctly.
- Ensure slice/step numbering is consistent across all three documents.
- Ensure impacted files mentioned in PRD appear in the implementation plan steps.

## Output

After creating all three files, report:
1. The phase number assigned
2. Summary of epics/scope defined
3. Number of implementation steps
4. File paths created

## Repository guidance

- All phase documents are written in Korean following existing convention.
- Keep the same structural patterns visible in existing phase documents.
- Do not modify existing phase documents unless explicitly asked.
- Preserve the separation between PRD (what/why), implementation plan (how/sequence), and task (tracking/evidence).

See `references/` for document templates.
