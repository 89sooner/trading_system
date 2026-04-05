# Task Template

This template defines the structure for `phase_{N}_task.md` documents.

## Required sections

```markdown
# Phase {N} Task Breakdown

## Usage

- 이 파일은 Phase {N} 구현 진행 상황과 검증 증적을 기록한다.
- 체크박스는 실제 구현 작업과 검증 기준을 뜻한다.
- 각 slice가 끝날 때 `Execution Log`를 갱신한다.
- PRD 수준 범위는 `phase_{N}_prd.md`를 기준으로 한다.
- 상세 설계와 순서는 `phase_{N}_implementation_plan.md`를 기준으로 한다.

## Status Note

- 이 문서는 `prd/phase_{N}_prd.md`의 실행 추적 문서다.
- 현재 체크박스는 active backlog를 slice 단위로 분해한 것이며, 아직 구현 완료를 의미하지 않는다.

## Phase {N}-0. {Step 0 제목}

- [ ] {구현/검증 항목}
- [ ] {구현/검증 항목}
...

Exit criteria:
- {이 단계의 종료 기준}

## Phase {N}-1. {Step 1 제목}

- [ ] {구현/검증 항목}
- [ ] {구현/검증 항목}
...

Exit criteria:
- {이 단계의 종료 기준}

## Phase {N}-{M}. {마지막 Step 제목}
...

## Verification Checklist

### Required unit tests

- [ ] `pytest tests/unit/{관련 테스트}.py -q`
...

### Required integration tests

- [ ] `pytest tests/integration/{관련 테스트}.py -q`
...

### Broader regression

- [ ] 관련 API/config/live loop 회귀 테스트 실행
- [ ] touched area 통과 후 broader regression 실행

### Manual verification

- [ ] {수동 확인 항목}
...

## Execution Log

### Date
- {구현 시작 시 날짜 기입}

### Owner
- {구현 주체}

### Slice completed
- {완료된 slice/step 기록}

### Scope implemented
- {구현된 범위 요약}

### Files changed
- {변경된 파일 목록}

### Commands run
- {실행한 검증 명령어와 결과}

### Validation results
- {검증 결과 요약}

### Risks / follow-up
- {잔여 리스크 및 후속 작업}
```

## Writing rules

- Write in Korean.
- All checkboxes start as `- [ ]` (unchecked). Never pre-check items in a new document.
- Each phase section maps 1:1 to a step in the implementation plan.
- Task items should be concrete and verifiable, not vague ("구현 확인" is bad, "multi-symbol preflight 요청 시 모든 심볼에 대해 readiness 결과 반환 확인" is good).
- Exit criteria should match the implementation plan's exit criteria.
- Execution Log starts empty — it gets filled during actual implementation.
- Verification Checklist should include actual pytest command paths where possible.
