import axios from 'axios'
import type { TwinRunRequest, TwinRunResult, CycleResult } from '../types'

const BASE = '/api'

export const api = {
  health: () => axios.get('/health').then(r => r.data),

  twin: {
    run: (req: TwinRunRequest): Promise<TwinRunResult> =>
      axios.post(`${BASE}/twin/run`, req).then(r => r.data),
    getState: (wellId: string) =>
      axios.get(`${BASE}/wells/${wellId}/state`).then(r => r.data),
    getHistory: (wellId: string) =>
      axios.get(`${BASE}/wells/${wellId}/history`).then(r => r.data),
    reset: (wellId: string) =>
      axios.post(`${BASE}/wells/${wellId}/reset`).then(r => r.data),
  },

  css: {
    run: (params: Partial<TwinRunRequest>): Promise<CycleResult> =>
      axios.post(`${BASE}/css/run`, params).then(r => r.data),
  },

  risk: {
    score: (params: Record<string, number>) =>
      axios.post(`${BASE}/risk/score`, params).then(r => r.data),
  },
}
