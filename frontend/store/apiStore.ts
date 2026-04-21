import { create } from "zustand";
import { persist } from "zustand/middleware";

function resolveDefaultBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (configured?.trim()) return configured.trim().replace(/\/$/, "");
  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}:8000/api/v1`;
  }
  return "http://127.0.0.1:8000/api/v1";
}

const DEFAULT_BASE_URL = resolveDefaultBaseUrl();
const STORAGE_KEY = "ts_api_base_url";
const LEGACY_KEY = "apiBaseUrl";

function normalizeBaseUrl(url: string): string {
  const trimmed = url.trim();
  if (!trimmed) return DEFAULT_BASE_URL;
  return trimmed.endsWith("/") ? trimmed.slice(0, -1) : trimmed;
}

interface ApiStore {
  baseUrl: string;
  apiKey: string;
  setBaseUrl: (url: string) => void;
  setApiKey: (key: string) => void;
}

export const useApiStore = create<ApiStore>()(
  persist(
    (set) => ({
      baseUrl: DEFAULT_BASE_URL,
      apiKey: "",
      setBaseUrl: (url) => set({ baseUrl: normalizeBaseUrl(url) }),
      setApiKey: (key) => set({ apiKey: key.trim() }),
    }),
    {
      name: STORAGE_KEY,
      partialize: (state) => ({ baseUrl: state.baseUrl, apiKey: state.apiKey }),
      migrate: (persisted) => {
        // Migrate from legacy 'apiBaseUrl' plain-string key if present
        if (typeof window !== "undefined") {
          const legacy = localStorage.getItem(LEGACY_KEY);
          if (legacy) {
            localStorage.removeItem(LEGACY_KEY);
            const state = persisted as { baseUrl?: string; apiKey?: string } | null;
            if (!state?.baseUrl) {
              return { baseUrl: normalizeBaseUrl(legacy), apiKey: state?.apiKey ?? "" };
            }
          }
        }
        const state = (persisted as { baseUrl?: string; apiKey?: string } | null) ?? {};
        const normalizedDefault = resolveDefaultBaseUrl();
        const normalizedBaseUrl = state.baseUrl ? normalizeBaseUrl(state.baseUrl) : normalizedDefault;
        const migratedBaseUrl =
          normalizedBaseUrl === "http://127.0.0.1:8000/api/v1" ? normalizedDefault : normalizedBaseUrl;
        return {
          baseUrl: migratedBaseUrl,
          apiKey: state.apiKey ?? "",
        };
      },
      version: 3,
    },
  ),
);
