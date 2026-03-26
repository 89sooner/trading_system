/**
 * dashboardPage.js — Live Dashboard page controller.
 * Polls /api/v1/dashboard/* every 5 seconds.
 */

const REFRESH_INTERVAL_MS = 5000;

function getApiBase() {
  return (localStorage.getItem("apiBaseUrl") || "http://127.0.0.1:8000/api/v1").replace(/\/$/, "");
}

function getApiKey() {
  const el = document.getElementById("api-key");
  return el ? el.value.trim() : "";
}

function apiHeaders() {
  const key = getApiKey();
  return key ? { "X-API-Key": key } : {};
}

async function fetchJson(path) {
  const res = await fetch(`${getApiBase()}${path}`, { headers: apiHeaders() });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function postJson(path, body) {
  const res = await fetch(`${getApiBase()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...apiHeaders() },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

// ── Status ────────────────────────────────────────────────────────────────

function setBadge(state) {
  const el = document.getElementById("state-badge");
  el.textContent = state || "–";
  el.className = `status-badge badge-${(state || "unknown").toLowerCase()}`;
}

function formatUptime(seconds) {
  if (seconds == null) return "–";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h}h ${m}m ${s}s`;
}

async function refreshStatus() {
  try {
    const data = await fetchJson("/dashboard/status");
    setBadge(data.state);
    document.getElementById("last-hb").textContent = data.last_heartbeat
      ? new Date(data.last_heartbeat).toLocaleTimeString()
      : "–";
    document.getElementById("uptime").textContent = formatUptime(data.uptime_seconds);
  } catch (e) {
    setBadge("unknown");
    document.getElementById("last-hb").textContent = "–";
    document.getElementById("uptime").textContent = "–";
  }
}

// ── Positions ─────────────────────────────────────────────────────────────

async function refreshPositions() {
  try {
    const data = await fetchJson("/dashboard/positions");
    document.getElementById("cash-value").textContent = data.cash;
    const tbody = document.getElementById("positions-body");
    if (!data.positions || data.positions.length === 0) {
      tbody.innerHTML = `<tr class="empty-row"><td colspan="4">No open positions.</td></tr>`;
    } else {
      tbody.innerHTML = data.positions
        .map(
          (p) => `<tr>
            <td>${p.symbol}</td>
            <td>${p.quantity}</td>
            <td>${p.average_cost}</td>
            <td>${p.unrealized_pnl ?? "–"}</td>
          </tr>`,
        )
        .join("");
    }
  } catch {
    document.getElementById("cash-value").textContent = "–";
  }
}

// ── Events ────────────────────────────────────────────────────────────────

function severityClass(sev) {
  if (!sev) return "";
  if (sev.includes("WARNING")) return "ev-tag-WARNING";
  if (sev.includes("ERROR") || sev.includes("CRITICAL")) return "ev-tag-ERROR";
  return "ev-tag-INFO";
}

async function refreshEvents() {
  try {
    const data = await fetchJson("/dashboard/events?limit=50");
    const feed = document.getElementById("event-feed");
    if (!data.events || data.events.length === 0) {
      feed.innerHTML = `<div class="event-item"><span class="ev-ts">–</span><span>No events yet.</span></div>`;
      return;
    }
    feed.innerHTML = [...data.events]
      .reverse()
      .map((e) => {
        const ts = new Date(e.timestamp).toLocaleTimeString();
        const cls = severityClass(e.severity);
        const payloadStr = Object.entries(e.payload || {})
          .map(([k, v]) => `${k}=${v}`)
          .join(" ");
        return `<div class="event-item">
          <span class="ev-ts">${ts}</span>
          <span class="ev-tag ${cls}">${e.severity}</span>
          <b>${e.event}</b>
          <span style="color:#6b7280;margin-left:0.5rem">${payloadStr}</span>
        </div>`;
      })
      .join("");
  } catch {
    /* silently update dot color */
  }
}

// ── Refresh cycle ─────────────────────────────────────────────────────────

function updateRefreshTs() {
  document.getElementById("last-refresh-ts").textContent = new Date().toLocaleTimeString();
}

async function refresh() {
  await Promise.allSettled([refreshStatus(), refreshPositions(), refreshEvents()]);
  updateRefreshTs();
}

// ── Control buttons ───────────────────────────────────────────────────────

async function sendControl(action) {
  const msg = document.getElementById("ctrl-msg");
  try {
    const data = await postJson("/dashboard/control", { action });
    msg.textContent = `✓ Action '${action}' applied. State: ${data.state}`;
    msg.style.color = "#22c55e";
    await refresh();
  } catch (e) {
    msg.textContent = `✗ ${e.message}`;
    msg.style.color = "#ef4444";
  }
}

document.getElementById("btn-pause").addEventListener("click", () => sendControl("pause"));
document.getElementById("btn-resume").addEventListener("click", () => sendControl("resume"));
document.getElementById("btn-reset").addEventListener("click", () => {
  if (confirm("Are you sure you want to RESET? This clears EMERGENCY state and returns to PAUSED."))
    sendControl("reset");
});

// ── Bootstrap ─────────────────────────────────────────────────────────────

// Prefill API base URL from localStorage
const savedBase = localStorage.getItem("apiBaseUrl");
if (savedBase) document.getElementById("api-base-url").value = savedBase;

refresh();
setInterval(refresh, REFRESH_INTERVAL_MS);
