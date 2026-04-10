# Verification Result

## 1. Target checked

`prd/phase_8_plan_review_from_codex.md`, `prd/phase_8_prd.md`, `prd/phase_8_implementation_plan.md`, `prd/phase_8_task.md` 기준으로 현재 워크트리의 Phase 8 변경사항이 실제로 잘 구현되었는지 검증했다.

## 2. What was inspected

- 문서:
  - `prd/phase_8_plan_review_from_codex.md`
  - `prd/phase_8_prd.md`
  - `prd/phase_8_implementation_plan.md`
  - `prd/phase_8_task.md`
- 백엔드 구현:
  - `src/trading_system/backtest/repository.py`
  - `src/trading_system/backtest/file_repository.py`
  - `src/trading_system/api/routes/backtest.py`
  - `src/trading_system/api/routes/dashboard.py`
  - `src/trading_system/api/schemas.py`
  - `src/trading_system/app/loop.py`
  - `src/trading_system/app/services.py`
  - `src/trading_system/app/equity_writer.py`
  - `src/trading_system/core/ops.py`
  - `src/trading_system/notifications/webhook.py`
- 프론트엔드 구현:
  - `frontend/app/runs/page.tsx`
  - `frontend/app/dashboard/page.tsx`
  - `frontend/hooks/useDashboardPolling.ts`
  - `frontend/lib/api/types.ts`
  - `frontend/lib/api/backtests.ts`
  - `frontend/lib/api/dashboard.ts`
- 테스트:
  - `tests/unit/test_file_repository.py`
  - `tests/unit/test_equity_timeseries.py`
  - `tests/unit/test_core_ops.py`
  - `tests/unit/test_webhook_notifier.py`
  - `tests/unit/test_sse_stream.py`
  - `tests/integration/test_backtest_run_api_integration.py`
  - `tests/unit/test_api_backtest_schema.py`

## 3. Validation evidence

- `pytest tests/unit/test_file_repository.py -q` → PASS (`11 passed`)
- `pytest tests/unit/test_equity_timeseries.py -q` → PASS (`6 passed`)
- `pytest tests/unit/test_core_ops.py -q` → PASS (`6 passed`)
- `pytest tests/unit/test_webhook_notifier.py -q` → PASS (`9 passed`)
- `pytest tests/unit/test_sse_stream.py -q` → 완료되지 않음
- `pytest tests/unit/test_sse_stream.py -vv -s` → `test_sse_connection_limit_returns_429`에서 진행이 멈춤
- `ruff check src/trading_system/backtest/file_repository.py src/trading_system/api/routes/backtest.py src/trading_system/api/routes/dashboard.py src/trading_system/api/schemas.py src/trading_system/app/loop.py src/trading_system/app/services.py src/trading_system/core/ops.py src/trading_system/app/equity_writer.py src/trading_system/notifications tests/unit/test_file_repository.py tests/unit/test_equity_timeseries.py tests/unit/test_sse_stream.py tests/unit/test_webhook_notifier.py` → FAIL
  - `src/trading_system/app/services.py` 기존 `E501` 2건
- `cd frontend && npx tsc --noEmit` → PASS
- `cd frontend && npm run lint` → PASS
- `cd frontend && npm run build` → PASS
- `rg -n "useDashboardStream|listBacktestRuns|getDashboardEquity|dashboard/equity|dashboard/stream|EventSource" frontend` → 결과 없음
- `rg -n "webhook|dashboard/stream|dashboard/equity|Phase 8|runs list|SSE" README.md configs/base.yaml` → 결과 없음

## 4. Decision

Needs fix

## 5. Findings

1. Phase 8-6/7 프론트엔드 통합은 아직 구현되지 않았다.
   - `/runs`는 여전히 `runsStore` + 개별 `getBacktestRun()` 조회에 의존한다.
   - 대시보드는 여전히 `useDashboardPolling()`만 사용한다.
   - `listBacktestRuns()`, `getDashboardEquity()`, `useDashboardStream()`, `EventSource` 연동이 없다.
   - 문서상 Phase 8의 핵심 가치 중 하나가 서버 목록 API 전환과 SSE/polling fallback인데, 현재 구현은 백엔드 API 추가에만 머문다.

2. Phase 8-8 문서/설정 반영이 빠져 있다.
   - `README.md`에 런 영속화, `/api/v1/dashboard/equity`, `/api/v1/dashboard/stream`, webhook env-var 사용법이 반영되지 않았다.
   - `configs/base.yaml`에도 webhook 예시 주석이 없다.
   - 이는 AGENTS.md의 “configuration shape 변경 시 `configs/`, `examples/`, `README.md` 함께 갱신” 원칙과 맞지 않는다.

3. `tests/unit/test_sse_stream.py`는 현재 재현 가능한 PASS 상태가 아니다.
   - 단일 파일 실행이 종료되지 않는다.
   - `-vv -s`로 보면 첫 케이스 `test_sse_connection_limit_returns_429`에서 멈춘다.
   - 따라서 `prd/phase_8_task.md`의 `36 passed`, `SSE endpoint ... 테스트 PASS`는 현재 워크트리에서 재현되지 않았다.

4. 신규 백엔드 기능은 상당 부분 구현됐지만, 계획 대비 검증 커버리지가 부족하다.
   - `FileBacktestRunRepository`, `GET /api/v1/backtests`, `GET /api/v1/dashboard/equity`, `GET /api/v1/dashboard/stream`, `WebhookNotifier` 자체는 코드상 존재한다.
   - 하지만 계획에 있던 `tests/integration/test_run_persistence_integration.py`는 없다.
   - `GET /api/v1/backtests` 목록 API 전용 통합 검증도 별도 추가되지 않았다.
   - SSE는 인증/연결 제한 외 실제 stream/heartbeat/event push 검증이 닫히지 않았다.

5. `prd/phase_8_task.md`의 상태 표시는 현재 코드 상태와 일관되지 않는다.
   - 상단 체크박스는 대부분 미체크 상태다.
   - 하단 `Execution Log`는 Phase 8-0~5 완료와 `pytest --tb=short -q → 214 passed`를 단정한다.
   - 현재 재검증 결과와 문서 서술이 충돌한다.

## 6. Scope compliance

- 백엔드 범위의 Phase 8-0~5는 대체로 계획 범위 안에서 구현됐다.
- 프론트엔드 범위의 Phase 8-6~7은 사실상 미착수 상태다.
- 문서/설정 정리인 Phase 8-8도 미완료다.
- 따라서 전체 Phase 8을 “잘 구현되었다”라고 보기는 어렵고, “백엔드 기반 공사만 선행 구현되었다”가 더 정확하다.

## 7. Remaining risks or unknowns

- `dashboard.py`의 SSE endpoint는 존재하지만, 현재 테스트가 멈추는 원인이 해결되지 않아 운영 전 검증이 부족하다.
- `FileBacktestRunRepository`는 구현됐지만 서버 재시작 보존 시나리오를 통합 테스트로 아직 닫지 못했다.
- 프론트엔드가 새 API를 소비하지 않기 때문에, 사용자는 Phase 8의 핵심 개선 효과를 아직 체감할 수 없다.
- 전체 `pytest --tb=short -q`는 이번 검증 중 종료 결과를 회수하지 못했다. 현재 문서에 적힌 `214 passed`는 별도 재확인이 필요하다.

## 8. Adversarial Review 동의 항목 (Claude 구현자 관점)

아래는 Codex adversarial review(2026-04-10)의 findings 중 구현자로서 타당하다고 판단하는 항목이다.

### [high] SSE 인증이 실제 보안 레이어와 충돌한다 — **동의**

`dashboard.py`의 `stream_events()`는 `api_key` query param을 직접 검증하지만, 이 로직은 미들웨어가 먼저 차단하면 실행조차 되지 않는다.

`security.py`의 `_extract_api_key()`는 `x-api-key` / `authorization` 헤더만 읽는다. `TRADING_SYSTEM_ALLOWED_API_KEYS`가 설정된 배포 환경에서는 미들웨어가 headers 기반으로 401을 반환하기 때문에, 브라우저 `EventSource`가 query param으로 키를 보내도 route handler가 검증할 기회조차 없다.

테스트가 통과하는 이유는 `conftest.py`의 `_bypass_api_key_auth` fixture가 `TRADING_SYSTEM_ALLOWED_API_KEYS=""`로 강제해서 미들웨어 인증을 비활성화하기 때문이다. 실제 운영 환경(`.env`에 키 설정)에서는 SSE 연결이 항상 401로 실패한다.

**수정 방향**: `security.py`의 미들웨어가 SSE 경로(`/api/v1/dashboard/stream`)에 한해 query param `api_key`도 허용하도록 수정하거나, `_extract_api_key()`를 확장해야 한다. route-level 중복 검증은 제거 가능.

### [high] `_index.json` 동시 쓰기 경합 — **동의**

`FileBacktestRunRepository.save()`와 `delete()`는 `_read_index()` → 수정 → `_write_index()` 패턴을 사용하며, `_write_index()` 내부의 임시 파일 경로가 `_index.json.tmp`로 고정되어 있다.

두 요청이 동시에 `save()`를 호출하면:
1. 둘 다 같은 구 인덱스를 읽는다.
2. 각자 항목을 추가한 뒤 같은 `.tmp` 경로에 쓴다.
3. 나중에 `os.replace()` 하는 쪽이 이긴다 → 앞서 쓴 항목이 누락된다.

현재 백테스트 실행이 동기(`def create_backtest_run`)이므로 FastAPI의 threadpool 내에서 동시 실행이 가능하다. 실제 동시 요청이 드물더라도, 인덱스 유실은 silent이므로 위험도가 높다.

**수정 방향**: `threading.Lock()`을 인스턴스 수준에서 보유하고, `save()` / `delete()` / `clear()` / `rebuild_index()` 전체를 해당 lock으로 보호한다. 임시 파일은 `uuid`나 `tempfile.mkstemp`로 유일하게 생성한다.

### [medium] Webhook 스레드 언바운드 생성 — **부분 동의**

`WebhookNotifier.notify()`는 이벤트마다 새 daemon thread를 생성하고, 각 thread 안에서 새 event loop를 만들어 HTTP 요청을 보낸다. queue, pool, backpressure가 없다.

라이브 루프 정상 운영 시 이벤트 빈도는 낮으므로 실제 thread 폭발 가능성은 제한적이다. 그러나:
- `system.error` 루프 버그 등으로 같은 이벤트가 단시간 다수 발생하면 스레드가 급증한다.
- daemon thread이므로 프로세스 종료 시 in-flight 전송이 무음으로 손실된다.
- 각 thread가 새 `asyncio.new_event_loop()`를 생성/소멸하는 오버헤드가 누적된다.

**수정 방향**: 단일 background worker thread + `queue.Queue(maxsize=N)`으로 교체하면 bounded 보장과 종료 시 drain 처리가 모두 가능하다.

---

## 9. Next loop handoff

Goal:
Phase 8을 문서 기준으로 실제 완료 상태까지 끌어올린다.

Why another loop is needed:
백엔드 기반 기능은 상당 부분 들어갔지만, 프론트엔드 통합, 문서 갱신, SSE 테스트 안정화가 남아 있어 현재는 부분 완료 상태다.

Files likely in scope:
- `frontend/app/runs/page.tsx`
- `frontend/app/dashboard/page.tsx`
- `frontend/hooks/useDashboardStream.ts`
- `frontend/lib/api/backtests.ts`
- `frontend/lib/api/dashboard.ts`
- `frontend/lib/api/types.ts`
- `tests/unit/test_sse_stream.py`
- `tests/integration/test_backtest_run_api_integration.py`
- `tests/integration/test_run_persistence_integration.py`
- `README.md`
- `configs/base.yaml`
- `prd/phase_8_task.md`

Known issues:
- `/runs`는 아직 서버 목록 API를 쓰지 않는다.
- dashboard는 아직 SSE/equity history를 쓰지 않는다.
- `test_sse_stream.py`는 현재 멈춘다.
- task 문서의 완료 주장과 실제 상태가 다르다.

Validation to rerun:
- `pytest tests/unit/test_sse_stream.py -q`
- `pytest tests/integration/test_backtest_run_api_integration.py -q`
- `pytest tests/integration/test_run_persistence_integration.py -q`
- `pytest --tb=short -q`
- `ruff check src/ tests/`
- `cd frontend && npx tsc --noEmit`
- `cd frontend && npm run lint`
- `cd frontend && npm run build`
- `cd frontend && npm run test:e2e`
