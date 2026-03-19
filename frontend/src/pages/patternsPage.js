import {
  listPatternSets,
  savePatternSet,
  trainPatterns,
  userMessageForError,
} from "../api/client.js";
import { initApiBaseControl } from "./apiBaseControl.js";

const form = document.getElementById("pattern-form");
const message = document.getElementById("pattern-message");
const previewBody = document.getElementById("pattern-preview-body");
const saveButton = document.getElementById("save-pattern-button");
const refreshButton = document.getElementById("refresh-patterns");
const listBody = document.getElementById("pattern-sets-body");
const detailLink = document.getElementById("pattern-detail-link");

let latestPreview = null;

function setMessage(text, isError = false) {
  message.textContent = text;
  message.classList.toggle("error", isError);
}

function parseExamples(rawText) {
  const blocks = String(rawText)
    .trim()
    .split(/\n\s*\n/)
    .map((block) => block.trim())
    .filter(Boolean);

  return blocks.map((block) => {
    const lines = block.split("\n").map((line) => line.trim()).filter(Boolean);
    const [labelLine, ...barLines] = lines;
    const label = labelLine.replace(/^label=/i, "").trim();
    return {
      label,
      bars: barLines.map((line) => {
        const [timestamp, open, high, low, close, volume] = line.split(",").map((value) => value.trim());
        return { timestamp, open, high, low, close, volume };
      }),
    };
  });
}

function renderPreview(patternSet) {
  previewBody.innerHTML = "";
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
    previewBody.append(tr);
  }
}

function renderSavedPatternSets(patternSets) {
  listBody.innerHTML = "";
  for (const patternSet of patternSets) {
    const tr = document.createElement("tr");
    const link = document.createElement("a");
    link.href = `./pattern.html?pattern_set_id=${encodeURIComponent(patternSet.pattern_set_id)}`;
    link.textContent = "Open";
    const action = document.createElement("td");
    action.append(link);
    for (const value of [
      patternSet.pattern_set_id,
      patternSet.name,
      patternSet.symbol,
      String(patternSet.patterns.length),
    ]) {
      const td = document.createElement("td");
      td.textContent = value;
      tr.append(td);
    }
    tr.append(action);
    listBody.append(tr);
  }
}

async function refreshPatternSets() {
  try {
    renderSavedPatternSets(await listPatternSets());
  } catch (error) {
    setMessage(userMessageForError(error), true);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage("Training preview...", false);
  saveButton.disabled = true;

  const formData = new FormData(form);
  const payload = {
    name: String(formData.get("patternName")).trim(),
    symbol: String(formData.get("patternSymbol")).trim().toUpperCase(),
    default_threshold: Number(formData.get("patternThreshold")),
    examples: parseExamples(formData.get("patternExamples")),
  };

  try {
    latestPreview = await trainPatterns(payload);
    renderPreview(latestPreview);
    detailLink.hidden = true;
    saveButton.disabled = false;
    setMessage(`Preview ready: ${latestPreview.pattern_set_id}`, false);
  } catch (error) {
    latestPreview = null;
    setMessage(userMessageForError(error), true);
  }
});

saveButton.addEventListener("click", async () => {
  if (!latestPreview) {
    return;
  }
  setMessage("Saving pattern set...", false);
  try {
    const saved = await savePatternSet(latestPreview);
    detailLink.href = `./pattern.html?pattern_set_id=${encodeURIComponent(saved.pattern_set_id)}`;
    detailLink.hidden = false;
    await refreshPatternSets();
    setMessage(`Saved pattern set: ${saved.pattern_set_id}`, false);
  } catch (error) {
    setMessage(userMessageForError(error), true);
  }
});

refreshButton.addEventListener("click", refreshPatternSets);
initApiBaseControl();
refreshPatternSets();
