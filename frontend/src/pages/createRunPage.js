import {
  createBacktestRun,
  listStrategyProfiles,
  userMessageForError,
} from "../api/client.js";
import { initApiBaseControl } from "./apiBaseControl.js";
import { saveRun } from "../state/runStore.js";

const form = document.getElementById("backtest-form");
const message = document.getElementById("form-message");
const submitButton = document.getElementById("submit-button");
const strategyProfileSelect = document.getElementById("strategy-profile");

function setMessage(text, isError = false) {
  message.textContent = text;
  message.classList.toggle("error", isError);
}

function buildPayload(formData) {
  const strategyProfile = String(formData.get("strategyProfile") || "").trim();
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
    strategy: strategyProfile
      ? {
          type: "pattern_signal",
          profile_id: strategyProfile,
        }
      : null,
  };
}

async function loadStrategyProfiles() {
  try {
    const profiles = await listStrategyProfiles();
    for (const profile of profiles) {
      const option = document.createElement("option");
      option.value = profile.strategy_id;
      option.textContent = `${profile.name} (${profile.strategy_id})`;
      strategyProfileSelect.append(option);
    }
  } catch (_error) {
    setMessage("Strategy profiles could not be loaded. Backtest form still supports default momentum.", true);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitButton.disabled = true;
  setMessage("Submitting...", false);

  const formData = new FormData(form);
  const payload = buildPayload(formData);
  const strategyProfile = payload.strategy?.profile_id ?? null;

  try {
    const created = await createBacktestRun(payload);
    saveRun({
      runId: created.run_id,
      status: created.status,
      symbol: payload.symbols[0],
      strategyProfile,
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
loadStrategyProfiles();
