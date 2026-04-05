import { requestJson } from './client'
import type { PatternSetDTO } from './types'

export interface PatternTrainRequest {
  name: string
  symbol: string
  default_threshold: number
  examples: Array<{ label: string; bars: Array<{ timestamp: string; open: string; high: string; low: string; close: string; volume: string }> }>
}

export const trainPatterns = (payload: PatternTrainRequest) =>
  requestJson<PatternSetDTO>('/patterns/train', { method: 'POST', body: JSON.stringify(payload) })

export const savePatternSet = (payload: PatternSetDTO) =>
  requestJson<PatternSetDTO>('/patterns', { method: 'POST', body: JSON.stringify(payload) })

export const listPatternSets = () => requestJson<PatternSetDTO[]>('/patterns')
export const getPatternSet = (id: string) =>
  requestJson<PatternSetDTO>(`/patterns/${encodeURIComponent(id)}`)
