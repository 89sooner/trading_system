# Release gate checklist

## Purpose

라이브 주문 전환 전에 필수 운영 게이트를 동일한 기준으로 점검한다.
현재 저장소 기준으로 `--mode live`는 기본 preflight를 수행하고,
`--live-execution paper` 지정 시 실주문 없이 페이퍼 실행 루프를 수행한다.

## Gate 1: Test baseline

- [ ] `pytest -m smoke -q` 통과
- [ ] `pytest -m "not smoke" -q` 통과
- [ ] 최근 변경 영역(설정/리스크/실행 경계)에 대한 신규 회귀 테스트 포함

## Gate 2: Config and secret baseline

- [ ] `configs/base.yaml`이 최신 스키마와 일치
- [ ] 운영 환경의 `TRADING_SYSTEM_API_KEY` 주입 확인
- [ ] 시크릿이 코드/로그/티켓에 노출되지 않음

## Gate 3: Runtime preflight baseline

- [ ] `python -m trading_system.app.main --mode live --symbols BTCUSDT` preflight 성공
- [ ] `python -m trading_system.app.main --mode live --symbols BTCUSDT --live-execution paper` paper 실행 성공
- [ ] 잘못된 설정 입력 시 명확한 사용자 오류 메시지 반환 확인
- [ ] 다중 심볼 제한/현 스캐폴드 제약이 운영자에게 공유됨

## Gate 4: Incident drill baseline

- [ ] 데이터 끊김 시나리오 점검(incident-response 시나리오 A)
- [ ] 주문 실패 시나리오 점검(incident-response 시나리오 B)
- [ ] 시계열 지연 시나리오 점검(incident-response 시나리오 C)

## Gate 5: Sign-off

- [ ] 개발 책임자 승인
- [ ] 운영 책임자 승인
- [ ] 롤백 담당자 및 연락 채널 확인

## Notes

- 본 체크리스트 통과는 실제 라이브 주문 구현 완료를 의미하지 않는다.
- 실제 주문 전환 전에는 브로커 어댑터/지속성/알림 체계를 추가해야 한다.
