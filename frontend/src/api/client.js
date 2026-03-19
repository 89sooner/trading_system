const DEFAULT_BASE_URL = "http://127.0.0.1:8000/api/v1";
const STORAGE_KEY = "ts_api_base_url";

export class ApiError extends Error {
  constructor(kind, message, status = null, payload = null) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
    this.payload = payload;
  }
}

function normalizeBaseUrl(baseUrl) {
  const trimmed = String(baseUrl).trim();
  if (trimmed.length === 0) {
    return DEFAULT_BASE_URL;
  }
  return trimmed.endsWith("/") ? trimmed.slice(0, -1) : trimmed;
}

export function getConfiguredApiBaseUrl() {
  const configured = window.localStorage.getItem(STORAGE_KEY);
  return normalizeBaseUrl(configured || DEFAULT_BASE_URL);
}

export function setConfiguredApiBaseUrl(baseUrl) {
  const normalized = normalizeBaseUrl(baseUrl);
  window.localStorage.setItem(STORAGE_KEY, normalized);
  return normalized;
}

function resolveBaseUrl() {
  return getConfiguredApiBaseUrl();
}

async function requestJson(path, options = {}) {
  const url = `${resolveBaseUrl()}${path}`;
  let response;

  try {
    response = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch (_networkError) {
    throw new ApiError("network", "Cannot reach backend API. Check host/port.");
  }

  const rawBody = await response.text();
  let parsed = null;
  if (rawBody) {
    try {
      parsed = JSON.parse(rawBody);
    } catch (_syntaxError) {
      parsed = null;
    }
  }

  if (response.ok) {
    return parsed;
  }

  if (response.status >= 400 && response.status < 500) {
    throw new ApiError(
      "validation",
      parsed?.message || parsed?.detail || "Validation error from backend.",
      response.status,
      parsed,
    );
  }

  if (response.status >= 500) {
    throw new ApiError(
      "server",
      parsed?.message || "Server error while handling request.",
      response.status,
      parsed,
    );
  }

  throw new ApiError("http", `Unexpected HTTP status: ${response.status}`, response.status, parsed);
}

export async function createBacktestRun(payload) {
  return requestJson("/backtests", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getBacktestRun(runId) {
  return requestJson(`/backtests/${encodeURIComponent(runId)}`);
}

export async function trainPatterns(payload) {
  return requestJson("/patterns/train", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function savePatternSet(payload) {
  return requestJson("/patterns", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listPatternSets() {
  return requestJson("/patterns");
}

export async function getPatternSet(patternSetId) {
  return requestJson(`/patterns/${encodeURIComponent(patternSetId)}`);
}

export async function createStrategyProfile(payload) {
  return requestJson("/strategies", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listStrategyProfiles() {
  return requestJson("/strategies");
}

export async function getStrategyProfile(strategyId) {
  return requestJson(`/strategies/${encodeURIComponent(strategyId)}`);
}

export function userMessageForError(error) {
  if (!(error instanceof ApiError)) {
    return "Unexpected error occurred in client.";
  }

  if (error.kind === "network") {
    return "네트워크 오류: 백엔드 서버에 연결할 수 없습니다. 서버 실행 상태를 확인하세요.";
  }
  if (error.kind === "validation") {
    return `요청 검증 오류(4xx): ${error.message}`;
  }
  if (error.kind === "server") {
    return `서버 오류(5xx): ${error.message}`;
  }
  return `HTTP 오류: ${error.message}`;
}
