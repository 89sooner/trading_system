# KRX CSV 기능 검증 루프 (2026-03-17)

## 문제 1-Pager

### Context

- 구현된 기능은 앱 설정과 서비스 조립 경로를 통해 KRX 스타일 심볼(예: `005930`)에 대한 CSV 기반 백테스트를 추가했다.
- 이전 검증 루프에서는 두 가지 근거 공백이 식별되었다: (1) 승인된 대상에 대한 명시적 추적성, (2) 명령 단위 런타임 검증 근거.

### Problem

- 저장소에는 이 기능을 위한 코드와 테스트가 있었지만, 승인 대상과 실제 검증 결과를 연결하는 명시적 검증 아티팩트는 없었다.

### Goal

- 대상 → 구현 범위 → 실행된 검증 근거를 연결하는 최소한의 지속 가능한 검증 아티팩트를 남긴다.

### Non-Goals

- 트레이딩 로직 변경 없음
- 설정 스키마 변경 없음
- 런타임 모듈 리팩터링 없음

### Constraints

- 이번 루프는 작고 안전하게 유지한다.
- 기존 테스트를 사용하고 신규 의존성은 추가하지 않는다.
- 결정적 동작을 유지한다.

## 승인 대상 참조

- 이번 루프에서 사용한 명시적 대상: feature commit `411b0ca` (`Add CSV backtest provider path for KRX symbols`) 및 해당 범위 파일.

## 옵션 비교 (결정 전)

- 옵션 A: 근거를 일회성 CI/로컬 로그에만 남긴다.
  - 장점: 저장소 diff가 없다.
  - 단점: 감사 가능성이 낮고, 이후 루프에서 지속 가능한 근거로 인용할 수 없다.
  - 위험: 동일한 검증 공백이 반복된다.
- 옵션 B: 저장소 안에 작은 런북 검증 노트를 추가한다.
  - 장점: 한 파일에서 지속 가능하고, 리뷰 가능하며, 추적성이 확보된다.
  - 단점: 유지해야 할 문서 파일이 하나 늘어난다.
  - 위험: 시간이 지나면 문서가 낡을 수 있다.

**선택:** 옵션 B (가장 단순한 지속 경로).

## 점검한 범위

- `src/trading_system/app/settings.py`
- `src/trading_system/app/services.py`
- `src/trading_system/app/main.py`
- `src/trading_system/data/provider.py`
- `tests/unit/test_app_services.py`
- `tests/unit/test_app_main.py`
- `README.md`
- `configs/krx_csv.yaml`
- `examples/sample_backtest_krx.yaml`

## 검증 근거

- `pytest tests/unit/test_app_services.py -q` → 통과 (`2 passed`)
- `pytest tests/unit/test_app_main.py -q` → 통과 (`6 passed`)
- `pytest -m smoke -q` → 통과 (`2 passed, 44 deselected`)

## 영향 메모

- 이번 루프에서는 프로덕션 코드를 변경하지 않았고, 검증 문서만 추가되었다.
- 런타임 동작은 변하지 않았으며, 위험은 문서 노후화 정도로 제한된다.

## 결정

- Pass

## 남은 위험 / 미확정 사항

- 이 아티팩트는 commit 수준의 승인 대상을 참조한다. 만약 프로세스상 issue/ADR 수준의 승인 연결이 필요하다면, 향후 docs-only 후속 작업에서 해당 ID를 추가해야 한다.

## 즉시 다음 액션

1. 감사 가능성을 위해 이 검증 노트를 정식 issue 또는 ADR ID와 연결한다.
2. 다음 루프 보고서에는 세 개 테스트 명령에 대한 CI job URL 또는 artifact 경로를 함께 남긴다.
3. 런타임 동작이 바뀌지 않는 한, 이 런북은 docs-only로 유지한다.

## 다음 루프 핸드오프

Goal:

- 승인 추적성을 commit 수준에서 issue/ADR 수준으로 강화한다.

Why another loop is needed:

- 현재 검증은 기술적으로 통과했지만, 거버넌스 추적성은 여전히 미해결 항목으로 남아 있다.

Files likely in scope:

- `docs/runbooks/krx-csv-verification-loop.md`
- `README.md` (발견된 링크를 갱신해야 하는 경우에만)
- 팀이 사용하는 issue/ADR 메타데이터 위치

Known issues:

- 승인 대상은 commit `411b0ca`에 연결되어 있으며, 아직 issue/ADR ID에는 연결되어 있지 않다.

Validation to rerun:

- `pytest tests/unit/test_app_services.py -q`
- `pytest tests/unit/test_app_main.py -q`
- `pytest -m smoke -q`
