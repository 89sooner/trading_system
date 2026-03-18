import { getBacktestRun, userMessageForError } from "../api/client.js";
import { renderTimeSeriesChart } from "../utils/charts.js";
import {
  formatDecimal,
  formatPercentFromRatio,
  formatUtcTimestamp,
} from "../utils/formatters.js";

const title = document.getElementById("run-title");
const message = document.getElementById("detail-message");
const summary = document.getElementById("summary");
const equityChart = document.getElementById("equity-chart");
const drawdownChart = document.getElementById("drawdown-chart");
const eventsBody = document.getElementById("events-table-body");
const refreshButton = document.getElementById("refresh-detail");

function setMessage(text, isError = false) {
  message.textContent = text;
  message.classList.toggle("error", isError);
}

function renderSummary(detail) {
  const stats = detail.result?.summary;
  if (!stats) {
    summary.textContent = "Result is not ready.";
    return;
  }

  const items = [
    ["Return", formatPercentFromRatio(stats.return)],
    ["Max Drawdown", formatPercentFromRatio(stats.max_drawdown)],
    ["Volatility", formatPercentFromRatio(stats.volatility)],
    ["Win Rate", formatPercentFromRatio(stats.win_rate)],
    ["Started (UTC)", formatUtcTimestamp(detail.started_at)],
    ["Finished (UTC)", formatUtcTimestamp(detail.finished_at)],
  ];
  summary.innerHTML = "";
  const grid = document.createElement("div");
  grid.className = "summary-grid";
  for (const [labelText, valueText] of items) {
    const wrapper = document.createElement("div");
    wrapper.className = "summary-item";
    const label = document.createElement("div");
    label.className = "label";
    label.textContent = labelText;
    const value = document.createElement("div");
    value.className = "value";
    value.textContent = valueText;
    wrapper.append(label, value);
    grid.append(wrapper);
  }
  summary.append(grid);
}

function renderEvents(detail) {
  const orders = detail.result?.orders ?? [];
  const rejections = detail.result?.risk_rejections ?? [];
  const rows = [
    ...orders.map((event) => ({ type: "fill", ...event })),
    ...rejections.map((event) => ({ type: "rejection", ...event })),
  ];

  eventsBody.innerHTML = "";
  for (const row of rows) {
    const tr = document.createElement("tr");
    const symbol = row.payload.symbol ?? "-";
    const qty = row.payload.filled_quantity ?? row.payload.requested_quantity ?? "-";
    const qtyText = formatDecimal(qty);
    const status = row.payload.status ?? (row.type === "rejection" ? "rejected" : "-");
    const cells = [row.type, row.event, symbol, qtyText, status];
    for (const value of cells) {
      const td = document.createElement("td");
      td.textContent = value;
      tr.append(td);
    }
    eventsBody.append(tr);
  }

  if (rows.length === 0) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td colspan="5">No fill/rejection events.</td>';
    eventsBody.append(tr);
  }
}

function renderCharts(detail) {
  const result = detail.result;
  if (!result) {
    equityChart.textContent = "No equity data.";
    drawdownChart.textContent = "No drawdown data.";
    return;
  }

  renderTimeSeriesChart(equityChart, result.equity_curve, "equity", "#2563eb");
  renderTimeSeriesChart(drawdownChart, result.drawdown_curve, "drawdown", "#dc2626");
}

function getRunId() {
  const params = new URLSearchParams(window.location.search);
  return params.get("run_id")?.trim() || "";
}

async function loadDetail() {
  const runId = getRunId();
  if (!runId) {
    setMessage("run_id query parameter is required.", true);
    return;
  }

  title.textContent = `Run ${runId}`;
  setMessage("Loading...", false);

  try {
    const detail = await getBacktestRun(runId);
    setMessage(`Status: ${detail.status}`, false);
    renderSummary(detail);
    renderCharts(detail);
    renderEvents(detail);
  } catch (error) {
    setMessage(userMessageForError(error), true);
  }
}

refreshButton.addEventListener("click", loadDetail);
loadDetail();
