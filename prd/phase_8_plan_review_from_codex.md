# Phase 8 Plan Review From Codex

검토 일자: 2026-04-09

검토 대상:
- `prd/phase_8_prd.md`
- 현재 `src/trading_system/` 및 `frontend/` 구현

업데이트:
- 본 문서는 최초 리뷰 이후 `prd/phase_8_prd.md`, `prd/phase_8_implementation_plan.md`, `prd/phase_8_task.md` 반영 상태를 기준으로 최종 보정되었다.

## Overall Verdict

`prd/phase_8_prd.md`는 **문제 정의와 방향 자체가 강했고, 초기 리뷰의 핵심 보정 사항도 대부분 반영됐다.**

특히 다음 판단은 적절하다.

- Phase 7.5 잔여 한계를 정확히 겨냥한다.
- 런 영속화, 서버 목록 API, SSE, equity history, webhook을 한 phase로 묶은 이유가 분명하다.
- 기존 REST contract를 유지하고 `SSE + polling fallback`으로 가겠다는 운영 전략도 현실적이다.
- 구현을 Slice 0~5로 나눈 구조 역시 실행 순서가 대체로 합리적이다.

현재 문서 세트 기준으로는, 이 PRD는 **바로 구현에 들어갈 수 있는 수준까지 대부분 닫혔다.**

최종 평가는 다음과 같다.

> Phase 8 문서 세트는 초기 리뷰에서 지적한 핵심 설계 공백을 대부분 해소했다.
> 특히 webhook 설정 경로, SSE 라우터 소유권, SSE 이벤트 발행 원천, 파일 영속화 복구 전략은 이제 구현 가능한 수준으로 정리됐다.
> 최종적으로 남아 있던 webhook 관련 표현 불일치도 정리되어, 현재는 문서 간 일관성이 양호하다.

## What Is Strong

### 1. 현재 운영 한계를 정확히 짚었다

근거:
- `prd/phase_8_prd.md:11-15`
- `src/trading_system/api/routes/backtest.py:36`
- `frontend/app/runs/page.tsx:41-55`
- `frontend/store/runsStore.ts:17-29`
- `frontend/hooks/useDashboardPolling.ts:58-75`
- `src/trading_system/api/routes/dashboard.py:113-131`

판단:
- 런 결과가 메모리 저장소에만 남는 점
- `/runs`가 localStorage 의존인 점
- equity 시계열이 클라이언트 메모리 누적인 점
- live dashboard가 polling 중심인 점

이 네 가지는 실제로 코드에 존재하는 구조적 한계다.

### 2. 하위 호환성과 fallback 전략이 실무적이다

근거:
- `prd/phase_8_prd.md:27-31`
- `prd/phase_8_prd.md:70-76`
- `prd/phase_8_prd.md:153-159`

판단:
- 기존 `/api/v1/*` REST 응답을 깨지 않겠다는 원칙은 맞다.
- SSE를 REST 대체가 아니라 보완으로 두는 것도 현재 frontend/backend 성숙도에 적합하다.
- `/runs`에서 서버 목록 API로 가되 `runsStore` fallback을 유지하겠다는 점도 현실적이다.

### 3. Slice 분해가 대체로 합리적이다

근거:
- `prd/phase_8_prd.md:288-329`

판단:
- 영속화 → 목록 API → equity history → SSE → webhook → 통합 검증 순서는 의존성 흐름과 잘 맞는다.
- 특히 목록 API보다 먼저 repository 경계를 정리하는 순서가 적절하다.

## Findings Status

### 1. Webhook/YAML 설정 통합 경로 문제는 반영 완료

상태:
- **해소됨**

반영 결과:
- webhook 설정 경로는 `config/settings.py`가 아니라 `app/settings.py` / `build_services()` 런타임 경로로 정리됐다.
- `configs/base.yaml`은 실제 파싱 대상이 아니라 예시 주석만 두는 방향으로 명시됐다.
- `prd/phase_8_prd.md`, `prd/phase_8_implementation_plan.md`, `prd/phase_8_task.md` 모두 이 결정을 따르고 있다.

### 2. SSE 엔드포인트 위치와 라우터 구조 충돌은 반영 완료

상태:
- **해소됨**

반영 결과:
- SSE 엔드포인트는 `/api/v1/dashboard/stream` 경로와 일치하게 `dashboard.py` 소유로 통일됐다.
- 별도 `stream.py` 전제는 제거됐고, 라우터 등록 충돌도 정리됐다.

### 3. SSE 이벤트 타입별 발행 원천 미정 문제는 반영 완료

상태:
- **해소됨**

반영 결과:
- PRD/implementation plan에 `status`, `position`, `event`, `equity`, `heartbeat` 각각의 source-of-truth와 trigger가 표 형태로 추가됐다.
- 이로써 logger subscriber 기반 이벤트와 라이브 루프 기반 이벤트의 경계가 분명해졌다.

### 4. query parameter API key 범위 문제는 반영 완료

상태:
- **해소됨**

반영 결과:
- query parameter API key는 `security.py` 전역 수정이 아니라 SSE endpoint 내부 예외 처리로 제한됐다.
- 기존 보안 표면을 넓히지 않는다는 의도가 문서에 명확히 적혔다.

### 5. 파일 영속화의 원자성/복구 전략은 반영 완료

상태:
- **해소됨**

반영 결과:
- 개별 `run` 파일을 source-of-truth로 두고 `_index.json`을 rebuildable cache로 두는 전략이 명시됐다.
- temp file + `os.replace()` 기반 atomic write, index 손상 시 재구축 전략도 문서화됐다.

### 6. equity JSONL truncate 복잡도 문제는 반영 완료

상태:
- **해소됨**

반영 결과:
- equity persistence는 append-only JSONL + 조회 시 최근 N개 반환으로 단순화됐다.
- physical compaction은 Phase 9 이후 과제로 미뤄져 구현 복잡도가 현실화됐다.

### 7. Phase 8 관련 문서 링크 문제는 반영 완료

상태:
- **해소됨**

반영 결과:
- Phase 8 관련 문서 링크와 참조 문맥이 정리됐다.
- 실행 추적 문서로 `prd/phase_8_task.md`가 중심 문서로 연결된다.

## Final Assessment

현재 `prd/phase_8_prd.md`, `prd/phase_8_implementation_plan.md`, `prd/phase_8_task.md`는 초기 Codex 리뷰의 핵심 지적사항을 실질적으로 반영했다.

최종적으로 확인된 상태는 다음과 같다.

1. webhook 설정 경로는 env-var 기반 `build_services()` 경로로 정리됐다.
2. SSE route 소유권은 `dashboard.py`로 일관되게 정리됐다.
3. SSE 이벤트별 발행 지점과 trigger가 문서화됐다.
4. file persistence의 source-of-truth와 atomic write 전략이 문서화됐다.
5. equity JSONL 전략은 append-only + recent read로 단순화됐다.
6. 남아 있던 webhook 관련 표현 불일치도 최종 수정으로 해소됐다.

따라서 현재 문서 세트는 **구현 착수 가능한 수준**으로 판단한다.
