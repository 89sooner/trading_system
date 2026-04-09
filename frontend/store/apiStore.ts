import { create } from "zustand";
import { persist } from "zustand/middleware";

const DEFAULT_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
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
      setApiKey: (key) => set({ apiKey: key }),
    }),
    {
      name: STORAGE_KEY,
      partialize: (state) => ({ baseUrl: state.baseUrl }),
      migrate: (persisted) => {
        // Migrate from legacy 'apiBaseUrl' plain-string key if present
        if (typeof window !== "undefined") {
          const legacy = localStorage.getItem(LEGACY_KEY);
          if (legacy) {
            localStorage.removeItem(LEGACY_KEY);
            const state = persisted as { baseUrl?: string } | null;
            if (!state?.baseUrl) {
              return { baseUrl: normalizeBaseUrl(legacy) };
            }
          }
        }
        return persisted as { baseUrl: string };
      },
      version: 1,
    },
  ),
);
