# PRD Template

This template defines the structure for `phase_{N}_prd.md` documents.

## Required sections

```markdown
# Phase {N} PRD

관련 문서:
- 이전 phase 범위/결과: `prd/phase_{N-1}_prd.md`
- 상세 구현 계획: `prd/phase_{N}_implementation_plan.md`
- 실행 및 검증 기록: `prd/phase_{N-1}_task.md`
- 실행 추적: `prd/phase_{N}_task.md`

## 문서 목적

{이 phase가 왜 필요한지, 이전 phase와의 관계, 이번 phase의 초점을 2-3문단으로 설명}

## Goal

{이번 phase의 핵심 목표를 명확히 기술. 반드시 달성해야 하는 원칙도 함께 나열}

## Current Baseline

{현재 시스템 상태를 bullet point로 정리. 이전 phase에서 완료된 것, 남은 것, 현재 제약사항}

## Non-Goals

{이번 phase에서 명시적으로 다루지 않는 항목. 범위 확장 방지를 위해 구체적으로 나열}

## Hard Decisions

### D-1. {결정 제목}
{결정 내용과 근거를 설명}

### D-2. {결정 제목}
...

## Product Requirements

### PR-1. {요구사항 제목}
{구체적인 요구사항 설명. 무엇이 어떻게 동작해야 하는지}

### PR-2. {요구사항 제목}
...

## Scope By Epic

### Epic A. {에픽 제목}

목표:
- {에픽의 핵심 목표}

포함:
- {구현 범위에 포함되는 항목}

제외:
- {명시적으로 제외되는 항목}

### Epic B. {에픽 제목}
...

## Impacted Files

### {그룹명 (예: Planning and task docs)}
- `파일 경로`

### {그룹명 (예: Configuration and runtime)}
- `파일 경로`

### {그룹명 (예: Validation and docs)}
- `파일 경로`

## Delivery Slices

### Slice 0. {제목}
- {이 slice에서 달성할 내용}

### Slice 1. {제목}
...

## Success Metrics

- {측정 가능한 성공 기준}
- ...

## Risks and Follow-up

- {잠재적 리스크와 후속 작업}
- ...
```

## Writing rules

- Write in Korean.
- Be specific: avoid vague statements like "improve performance" without measurable criteria.
- Non-Goals should prevent scope creep: list things that might seem related but are explicitly out.
- Hard Decisions should explain the rationale, not just the decision.
- Product Requirements should be testable.
- Epics should have explicit include/exclude boundaries.
- Delivery Slices should be ordered for incremental value delivery.
- Impacted Files should cover code, config, docs, and tests.
