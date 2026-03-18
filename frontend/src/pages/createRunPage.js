import { createBacktestRun, userMessageForError } from "../api/client.js";
import { initApiBaseControl } from "./apiBaseControl.js";
import { saveRun } from "../state/runStore.js";

const form = document.getElementById("backtest-form");
const message = document.getElementById("form-message");
const submitButton = document.getElementById("submit-button");

function setMessage(text, isError = false) {
  message.textContent = text;
  message.classList.toggle("error", isError);
}

function buildPayload(formData) {
  return {
    mode: "backtest",
    symbols: [String(formData.get("symbol")).trim().toUpperCase()],
    provider: "mock",
    broker: "paper",
    live_execution: "preflight",
    risk: {
      max_position: String(formData.get("maxPosition")),
      max_notional: String(formData.get("maxNotional")),
      max_order_size: String(formData.get("maxOrderSize")),
    },
    backtest: {
      starting_cash: "10000",
      fee_bps: String(formData.get("feeBps")),
      trade_quantity: String(formData.get("tradeQuantity")),
    },
  };
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitButton.disabled = true;
  setMessage("Submitting...", false);

  const formData = new FormData(form);
  const payload = buildPayload(formData);

  try {
    const created = await createBacktestRun(payload);
    saveRun({
      runId: created.run_id,
      status: created.status,
      symbol: payload.symbols[0],
      createdAt: new Date().toISOString(),
    });
    setMessage(`Run created: ${created.run_id}`, false);
    window.location.href = `./run.html?run_id=${encodeURIComponent(created.run_id)}`;
  } catch (error) {
    setMessage(userMessageForError(error), true);
  } finally {
    submitButton.disabled = false;
  }
});

initApiBaseControl();
