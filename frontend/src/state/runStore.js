const STORAGE_KEY = "ts_backtest_runs";

export function listRuns() {
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return [];
  }
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (_syntaxError) {
    return [];
  }
}

export function saveRun(run) {
  const runs = listRuns().filter((item) => item.runId !== run.runId);
  runs.unshift(run);
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(runs.slice(0, 100)));
}

export function updateRunStatus(runId, status) {
  const runs = listRuns().map((run) => (run.runId === runId ? { ...run, status } : run));
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(runs));
}
