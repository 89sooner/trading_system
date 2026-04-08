# Phase 7.5 Review From Codex v3

검토 일자: 2026-04-09

검토 대상:
- `prd/phase_7_5_review_from_codex_adversarial.md`
- 현재 `frontend/` 코드

## Overall Verdict

`phase_7_5_review_from_codex_adversarial.md`의 세 가지 finding 중, 현재 코드 기준으로는 **세 항목 모두 동의한다.**

이 지적들은 Phase 7.5 범위를 직접 겨냥한 것은 아니지만, 실제 운영 안전성과 입력 무결성 측면에서는 유효하다.

## Agreed Findings

### 1. Backtest 생성 폼은 숫자 필드를 `null`로 직렬화할 수 있다

동의 여부:
- **동의**

근거:
- [page.tsx](/home/roqkf/trading_system/frontend/app/page.tsx#L30) `handleSubmit`는 `FormData` 값을 바로 `Number(...)`로 변환한다.
- [page.tsx](/home/roqkf/trading_system/frontend/app/page.tsx#L40) ~ [page.tsx](/home/roqkf/trading_system/frontend/app/page.tsx#L48) 에서 `max_position`, `max_notional`, `max_order_size`, `starting_cash`, `fee_bps`, `trade_quantity` 모두 유효성 검증 없이 숫자화한다.
- 빈 문자열이나 비정상 입력은 `NaN`이 되며, JSON 직렬화 시 `NaN`은 `null`로 변한다.

판단:
- 이 경로는 실제로 클라이언트에서 잘못된 숫자 입력을 막지 못한다.
- backend가 기본값으로 보정하든 validation error를 반환하든, 현재 UI는 요청 자체를 안전하게 만들지 못한다.

### 2. Strategy profile 생성도 잘못된 숫자를 `null` 또는 비정상 값으로 보낼 수 있다

동의 여부:
- **동의**

근거:
- [StrategyForm.tsx](/home/roqkf/trading_system/frontend/components/strategies/StrategyForm.tsx#L18) 의 zod schema는 `tradeQuantity`, `thresholds`를 단순 문자열로만 받는다.
- [StrategyForm.tsx](/home/roqkf/trading_system/frontend/components/strategies/StrategyForm.tsx#L60) 에서 `trade_quantity: values.tradeQuantity ? Number(values.tradeQuantity) : null`
- [StrategyForm.tsx](/home/roqkf/trading_system/frontend/components/strategies/StrategyForm.tsx#L61) 에서 `threshold_overrides` 값을 `Number(v)`로 바로 변환한다.

판단:
- `tradeQuantity=""`는 `null`로 전송되고, 잘못된 threshold 문자열은 `Number(v)` 결과에 의존한다.
- 현재 폼 스키마는 “숫자여야 한다”는 제약을 전혀 강제하지 않는다.
- 따라서 adversarial review의 “invalid numeric thresholds can persist” 지적은 타당하다.

### 3. Runtime API key는 새로고침 후 사라진다

동의 여부:
- **동의**

근거:
- [apiStore.ts](/home/roqkf/trading_system/frontend/store/apiStore.ts#L27) ~ [apiStore.ts](/home/roqkf/trading_system/frontend/store/apiStore.ts#L31) 에 store는 `apiKey`와 `setApiKey`를 노출한다.
- [apiStore.ts](/home/roqkf/trading_system/frontend/store/apiStore.ts#L38) 에 초기 `apiKey`는 빈 문자열이다.
- [apiStore.ts](/home/roqkf/trading_system/frontend/store/apiStore.ts#L42) ~ [apiStore.ts](/home/roqkf/trading_system/frontend/store/apiStore.ts#L44) 의 `partialize`는 `baseUrl`만 persist한다.
- [client.ts](/home/roqkf/trading_system/frontend/lib/api/client.ts#L23) ~ [client.ts](/home/roqkf/trading_system/frontend/lib/api/client.ts#L29) 에서 `X-API-Key`는 store의 `apiKey`가 있을 때만 붙는다.
- 코드 검색상 settings UI는 [ApiSettingsBar.tsx](/home/roqkf/trading_system/frontend/components/shared/ApiSettingsBar.tsx)와 [README.md](/home/roqkf/trading_system/frontend/README.md) 에서 runtime API key 기능을 전제로 한다.

판단:
- 현재 구현은 base URL만 저장하고 API key는 저장하지 않는다.
- 따라서 페이지 reload 후 인증 헤더가 사라진다는 지적은 사실이다.
- 이것이 의도된 session-only 정책이라면 UI/문서에 명확히 드러나야 하는데, 현재는 그렇게 읽히지 않는다.

## Conclusion

`phase_7_5_review_from_codex_adversarial.md`에서 내가 동의하는 핵심은 다음 세 가지다.

1. backtest 생성 숫자 입력은 현재 클라이언트에서 안전하게 검증되지 않는다.
2. strategy profile 생성도 숫자 파싱 경로가 느슨하다.
3. runtime API key persistence는 현재 UI 기대와 store 동작이 어긋난다.

이 세 항목은 모두 실제 코드 근거가 있고, 후속 수정 가치가 있다.
