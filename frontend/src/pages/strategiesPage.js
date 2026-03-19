import {
  createStrategyProfile,
  listPatternSets,
  listStrategyProfiles,
  userMessageForError,
} from "../api/client.js";
import { initApiBaseControl } from "./apiBaseControl.js";

const form = document.getElementById("strategy-form");
const message = document.getElementById("strategy-message");
const patternSetSelect = document.getElementById("strategy-pattern-set");
const strategiesBody = document.getElementById("strategies-body");
const refreshButton = document.getElementById("refresh-strategies");

function setMessage(text, isError = false) {
  message.textContent = text;
  message.classList.toggle("error", isError);
}

function parseMap(rawText, parser = (value) => value) {
  const entries = String(rawText)
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => line.split("=").map((value) => value.trim()));
  return Object.fromEntries(entries.map(([key, value]) => [key, parser(value)]));
}

function renderStrategies(strategies) {
  strategiesBody.innerHTML = "";
  for (const strategy of strategies) {
    const tr = document.createElement("tr");
    for (const value of [
      strategy.strategy_id,
      strategy.name,
      strategy.strategy.pattern_set_id ?? "-",
      strategy.strategy.trade_quantity ?? "-",
    ]) {
      const td = document.createElement("td");
      td.textContent = String(value);
      tr.append(td);
    }
    strategiesBody.append(tr);
  }
}

async function refreshStrategyPage() {
  try {
    const [patternSets, strategies] = await Promise.all([listPatternSets(), listStrategyProfiles()]);
    patternSetSelect.innerHTML = "";
    for (const patternSet of patternSets) {
      const option = document.createElement("option");
      option.value = patternSet.pattern_set_id;
      option.textContent = `${patternSet.name} (${patternSet.pattern_set_id})`;
      patternSetSelect.append(option);
    }
    renderStrategies(strategies);
  } catch (error) {
    setMessage(userMessageForError(error), true);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(form);
  const tradeQuantity = String(formData.get("strategyTradeQuantity")).trim();
  const payload = {
    strategy_id: String(formData.get("strategyId")).trim(),
    name: String(formData.get("strategyName")).trim(),
    strategy: {
      type: "pattern_signal",
      pattern_set_id: String(formData.get("patternSet")).trim(),
      label_to_side: parseMap(formData.get("strategyLabelMap")),
      trade_quantity: tradeQuantity ? tradeQuantity : null,
      threshold_overrides: parseMap(formData.get("strategyThresholds"), Number),
    },
  };

  try {
    const created = await createStrategyProfile(payload);
    setMessage(`Saved strategy profile: ${created.strategy_id}`, false);
    await refreshStrategyPage();
  } catch (error) {
    setMessage(userMessageForError(error), true);
  }
});

refreshButton.addEventListener("click", refreshStrategyPage);
initApiBaseControl();
refreshStrategyPage();
