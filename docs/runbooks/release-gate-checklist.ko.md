# Release gate checklist

## Purpose

라이브 주문 전환 전에 필수 운영 게이트를 동일한 기준으로 점검한다.
현재 저장소 기준으로 `--mode live`는 기본 preflight를 수행하고,
`--live-execution paper` 지정 시 실주문 없이 페이퍼 실행 루프를 수행한다.
KIS 실주문 경로는 구현되어 있지만 `TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true` 뒤에 명시적으로 가드되어 있다.

## Gate 1: Test baseline

- [ ] `uv run --python .venv/bin/python --no-sync pytest -m smoke -q` 통과
- [ ] `uv run --python .venv/bin/python --no-sync pytest -m "not smoke" -q` 통과
- [ ] 최근 변경 영역(설정/리스크/실행 경계)에 대한 신규 회귀 테스트 포함

## Gate 2: Config and secret baseline

- [ ] `configs/base.yaml`이 현재 `config.settings.load_settings()` 스키마와 일치
- [ ] `portfolio_risk`를 사용할 경우 API payload, 앱 런타임 설정, 또는 typed YAML 설정 경로(`configs/base.yaml`, `examples/sample_live_kis.yaml`)가 문서화되어 있음
- [ ] 운영 환경의 `TRADING_SYSTEM_API_KEY` 또는 KIS 자격증명 주입 확인
- [ ] 시크릿이 코드/로그/티켓에 노출되지 않음

## Gate 3: Runtime preflight baseline

- [ ] `TRADING_SYSTEM_API_KEY=dummy-key uv run --python .venv/bin/python --no-sync -m trading_system.app.main --mode live --symbols BTCUSDT` preflight 성공
- [ ] `TRADING_SYSTEM_API_KEY=dummy-key uv run --python .venv/bin/python --no-sync -m trading_system.app.main --mode live --symbols BTCUSDT --live-execution paper` paper 실행 성공
- [ ] KIS 실주문 전환 대상이면 `--provider kis --broker kis` 조합의 preflight 성공
- [ ] 잘못된 설정 입력 시 명확한 사용자 오류 메시지 반환 확인
- [ ] 운영자가 백테스트/라이브 루프의 다중 심볼 지원 범위와 `/api/v1/live/preflight`의 하위 호환 응답 형태(`quote_summary` vs `quote_summaries`/`symbol_count`)를 이해함
- [ ] 대시보드 사용 대상이면 API 서버가 활성 live loop와 함께 시작되는 배포 방식이 준비됨
- [ ] durable backtest worker smoke 통과: run을 enqueue한 뒤 `python -m trading_system.app.backtest_worker --once`로 처리하고 `/api/v1/backtests/<run_id>`에서 progress/terminal 상태 확인
- [ ] Supabase 환경은 API 또는 worker 시작 전에 `scripts/migrations/006_add_backtest_jobs.sql` 적용 완료

## Gate 4: Incident drill baseline

- [ ] 데이터 끊김 시나리오 점검(incident-response 시나리오 A)
- [ ] 리스크 거절/비상 정지 시나리오 점검(incident-response 시나리오 B)
- [ ] 주문 실패/브로커 오류 시나리오 점검(incident-response 시나리오 C)
- [ ] 브로커 스냅샷 사용 환경이면 대사 불일치 시나리오 점검(incident-response 시나리오 D)
- [ ] `/api/v1/live/runtime/sessions/<session_id>/evidence`와 `/dashboard/sessions` route로 historical live session review 검증

## Gate 5: Sign-off

- [ ] 개발 책임자 승인
- [ ] 운영 책임자 승인
- [ ] 롤백 담당자 및 연락 채널 확인

## Notes

- KIS 실주문 경로는 존재하지만, 모든 게이트 통과 전까지 `TRADING_SYSTEM_ENABLE_LIVE_ORDERS=true`를 활성화하지 않는다.
- 일반 대사(reconciliation) 경로는 브로커 잔고 스냅샷이 있을 때만 동작한다. 현재 KIS 어댑터는 계좌 잔고 스냅샷을 제공하며, pending-order 신호가 불완전하면 fail-closed로 대사를 건너뛴다.
