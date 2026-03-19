import { getPatternSet, userMessageForError } from "../api/client.js";
import { initApiBaseControl } from "./apiBaseControl.js";

const title = document.getElementById("pattern-title");
const message = document.getElementById("pattern-detail-message");
const summary = document.getElementById("pattern-summary");
const body = document.getElementById("pattern-detail-body");

function setMessage(text, isError = false) {
  message.textContent = text;
  message.classList.toggle("error", isError);
}

function getPatternSetId() {
  const params = new URLSearchParams(window.location.search);
  return params.get("pattern_set_id")?.trim() || "";
}

function renderPatternSet(patternSet) {
  title.textContent = `${patternSet.name} (${patternSet.pattern_set_id})`;
  summary.innerHTML = `
    <div class="summary-grid">
      <div class="summary-item"><div class="label">Symbol</div><div class="value">${patternSet.symbol}</div></div>
      <div class="summary-item"><div class="label">Threshold</div><div class="value">${patternSet.default_threshold}</div></div>
      <div class="summary-item"><div class="label">Examples</div><div class="value">${patternSet.examples_count}</div></div>
      <div class="summary-item"><div class="label">Patterns</div><div class="value">${patternSet.patterns.length}</div></div>
    </div>
  `;
  body.innerHTML = "";
  for (const pattern of patternSet.patterns) {
    const tr = document.createElement("tr");
    for (const value of [
      pattern.label,
      String(pattern.lookback),
      String(pattern.sample_size),
      String(pattern.threshold),
    ]) {
      const td = document.createElement("td");
      td.textContent = value;
      tr.append(td);
    }
    body.append(tr);
  }
}

async function loadPatternSet() {
  const patternSetId = getPatternSetId();
  if (!patternSetId) {
    setMessage("pattern_set_id query parameter is required.", true);
    return;
  }

  try {
    const patternSet = await getPatternSet(patternSetId);
    renderPatternSet(patternSet);
    setMessage("Pattern set loaded.", false);
  } catch (error) {
    setMessage(userMessageForError(error), true);
  }
}

initApiBaseControl();
loadPatternSet();
