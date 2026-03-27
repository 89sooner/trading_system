import { requestJson } from './client'
import type { StrategyProfileDTO, StrategyConfigDTO } from './types'

export interface StrategyProfileCreateDTO {
  strategy_id: string
  name: string
  strategy: StrategyConfigDTO
}

export const createStrategyProfile = (payload: StrategyProfileCreateDTO) =>
  requestJson<StrategyProfileDTO>('/strategies', { method: 'POST', body: JSON.stringify(payload) })

export const listStrategyProfiles = () => requestJson<StrategyProfileDTO[]>('/strategies')
export const getStrategyProfile = (id: string) =>
  requestJson<StrategyProfileDTO>(`/strategies/${encodeURIComponent(id)}`)
