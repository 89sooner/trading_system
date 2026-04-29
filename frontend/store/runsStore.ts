import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface RunRecord {
  runId: string
  status: string
  symbol: string
  strategyProfile: string | null
  createdAt: string
  metadata?: {
    provider?: string | null
    broker?: string | null
    source?: string | null
  }
  job?: {
    worker_id?: string | null
    last_heartbeat_at?: string | null
    cancel_requested?: boolean
    progress?: {
      processed_bars: number
      total_bars: number
      percent: number
    }
  } | null
}

interface RunsStore {
  runs: RunRecord[]
  saveRun: (run: RunRecord) => void
  updateRunStatus: (runId: string, status: string) => void
}

export const useRunsStore = create<RunsStore>()(
  persist(
    (set, get) => ({
      runs: [],
      saveRun: (run) => {
        const filtered = get().runs.filter((r) => r.runId !== run.runId)
        set({ runs: [run, ...filtered].slice(0, 100) })
      },
      updateRunStatus: (runId, status) => {
        set({
          runs: get().runs.map((r) => (r.runId === runId ? { ...r, status } : r)),
        })
      },
    }),
    { name: 'ts_backtest_runs' },
  ),
)
