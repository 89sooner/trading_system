import { getBacktestRun, userMessageForError } from "../api/client.js";
import { formatUtcTimestamp } from "../utils/formatters.js";
import { listRuns, updateRunStatus } from "../state/runStore.js";

const tableBody = document.getElementById("runs-table-body");
const message = document.getElementById("runs-message");
const refreshButton = document.getElementById("refresh-runs");

function setMessage(text, isError = false) {
  message.textContent = text;
  message.classList.toggle("error", isError);
}

function renderRows(runs) {
  tableBody.innerHTML = "";
  for (const run of runs) {
    const tr = document.createElement("tr");
    const runId = document.createElement("td");
    runId.textContent = run.runId;
    const symbol = document.createElement("td");
    symbol.textContent = run.symbol ?? "-";
    const status = document.createElement("td");
    status.textContent = run.status;
    const createdAt = document.createElement("td");
    createdAt.textContent = formatUtcTimestamp(run.createdAt);
    const action = document.createElement("td");
    const link = document.createElement("a");
    link.href = `./run.html?run_id=${encodeURIComponent(run.runId)}`;
    link.textContent = "Open";
    action.append(link);
    tr.append(runId, symbol, status, createdAt, action);
    tableBody.append(tr);
  }
}

async function refreshStatuses() {
  const runs = listRuns();
  renderRows(runs);
  if (runs.length === 0) {
    setMessage("No runs saved yet.", false);
    return;
  }

  setMessage("Refreshing run statuses...", false);
  try {
    await Promise.all(
      runs.map(async (run) => {
        const detail = await getBacktestRun(run.runId);
        updateRunStatus(run.runId, detail.status);
      }),
    );
    renderRows(listRuns());
    setMessage("Status refresh completed.", false);
  } catch (error) {
    setMessage(userMessageForError(error), true);
  }
}

refreshButton.addEventListener("click", refreshStatuses);
refreshStatuses();
