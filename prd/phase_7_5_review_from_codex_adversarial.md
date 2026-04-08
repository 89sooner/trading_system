● Codex Adversarial Review

Target: working tree diff
Verdict: needs-attention

No-ship: the change can submit silently corrupted payloads in multiple write paths, and the advertised runtime API-key auth is dropped on reload.

Findings:

- [high] Backtest creation can silently null out risk and cash controls (app/page.tsx:40-48)
  handleSubmit converts every numeric field with Number(...) and never checks Number.isFinite. If the operator clears a field or enters an invalid value, the result is
  NaN; when this request body is JSON-encoded, those object properties become null. That means a run can be launched with missing risk limits or backtest parameters
  instead of being rejected client-side. Inference: whether this disables safeguards or triggers backend defaults depends on the API, but either outcome is materially
  unsafe for a run-creation flow.
  Recommendation: Validate all numeric inputs before calling createBacktestRun and block submission on non-finite values. A form schema (for example zod/react-hook-form)
  should enforce required ranges and serialize only valid numbers.
- [high] Strategy profile creation can persist invalid numeric thresholds as null (components/strategies/StrategyForm.tsx:57-61)
  The strategy form sends trade_quantity: Number(values.tradeQuantity) and parses threshold overrides with Number(v) without validating either result. Invalid entries such
  as an empty quantity or bullish=abc become NaN, which JSON serialization turns into null. That can store corrupted strategy configs or drop thresholds unexpectedly, and
  the bad state is hard to detect because the UI reports only the backend's generic error/success path.
  Recommendation: Reject non-numeric tradeQuantity and threshold values before submission. Parse into typed numbers only after validation and omit optional fields entirely
  when unset instead of sending null/NaN.
- [medium] Runtime API-key auth is lost on refresh despite the settings UI (store/apiStore.ts:34-45)
  The store exposes apiKey and setApiKey, and the layout renders an API settings control for operators, but the persisted state explicitly stores only baseUrl. After any
  reload, the API key is dropped from client state, so subsequent authenticated requests no longer send X-API-Key. For admin and other protected flows this creates a
  fragile auth boundary: the UI invites operators to rely on a setting that disappears mid-session.
  Recommendation: Persist apiKey as well, or remove the runtime API-key feature and documentation. If persisting the key is unacceptable, make the UI explicit that it is
  session-only and re-prompt after reload.

Next steps:

- Add input validation for all numeric write paths and verify the serialized payloads never contain null where numbers are required.
- Decide whether runtime API keys are supported; then align store persistence, UI copy, and request behavior with that decision.
