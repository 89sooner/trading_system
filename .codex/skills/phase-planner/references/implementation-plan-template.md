# Implementation Plan Template

This template defines the structure for `phase_{N}_implementation_plan.md` documents.

## Required sections

```markdown
# Phase {N} Implementation Plan

## Goal

{Phase의 구현 목표를 간결하게 기술. 핵심 구현 원칙을 번호 리스트로 나열}

## Preconditions

{구현 시작 전에 고정해야 할 범위와 제약사항}

## Locked Design Decisions

### 1. {설계 결정 제목}
{결정 내용, 방향, 고려사항을 구체적으로 기술}

### 2. {설계 결정 제목}
...

## Contract Deltas

## A. {서브시스템/계약 변경 제목}

대상:
- `파일 경로`

필수 변화:
- {반드시 변경되어야 하는 계약/동작}

비고:
- {추가 고려사항}

## B. {서브시스템/계약 변경 제목}
...

## Sequenced Implementation

### Step 0. {제목}

목적:
- {이 단계의 목적}

파일:
- `파일 경로`

구체 작업:
- {수행할 구체적 작업 항목}

종료 조건:
- {이 단계가 완료되었다고 판단하는 기준}

### Step 1. {제목}
...

## Validation Matrix

### Required unit tests
- {테스트 파일 또는 테스트 대상}

### Required integration tests
- {통합 테스트 범위}

### Manual verification
- {수동 확인이 필요한 항목}

## Recommended PR Slices

1. {PR 단위 설명}
2. ...

## Risks and Fallbacks

- {리스크 설명}

대응:
- {각 Step별 대응 전략}
```

## Writing rules

- Write in Korean.
- Steps should be sequenced so that each step builds on the previous one.
- Each step must have: purpose, files, concrete work items, exit criteria.
- Contract Deltas should describe what changes in the system's interfaces/behaviors.
- Preconditions should prevent scope creep during implementation.
- Design Decisions should be "locked" — not open questions, but resolved choices.
- PR Slices should align with implementation steps for reviewable increments.
- Risks and Fallbacks should have concrete mitigations, not just risk statements.
