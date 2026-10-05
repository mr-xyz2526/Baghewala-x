import axios from 'axios'
import type {
  TwinRunRequest,
  TwinRunResult,
  CycleResult,
  OptimizerRequest,
  OptimizationResult,
  RiskRequest,
  RiskScore,
  MLPredictResult,
  DynamometerCard,
} from '../types'

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
    inject: (params: {
      steam_rate_tpd: number
      steam_temp_c: number
      injection_days: number
      steam_quality: number
    }) =>
      axios.post(`${BASE}/css/inject`, null, { params }).then(r => r.data),
  },

  srp: {
    compute: (params: {
      spm: number
      fillage_pct: number
      water_cut_pct: number
      pump_depth_m: number
      structural_stroke_in: number
    }) => axios.post(`${BASE}/srp/compute`, params).then(r => r.data),

    dynamometer: (params: {
      spm: number
      surface_stroke_in: number
      pump_fillage_pct: number
      card_class: string
      rod_length_m?: number
      rod_diameter_in?: number
      plunger_diameter_in?: number
      damping_factor_s_inv?: number
      prefer_numerical?: boolean
    }): Promise<DynamometerCard> =>
      axios.post(`${BASE}/srp/dynamometer`, params).then(r => r.data),
  },

  ml: {
    predict: (params: {
      card_points: [number, number][]
      rod_diameter_in?: number
    }): Promise<MLPredictResult> =>
      axios.post(`${BASE}/ml/predict`, params).then(r => r.data),
    metrics: () =>
      axios.get(`${BASE}/ml/metrics`).then(r => r.data),
  },

  hydraulics: {
    compute: (params: Record<string, number>) =>
      axios.post(`${BASE}/hydraulics/compute`, params).then(r => r.data),
  },

  economics: {
    analyse: (params: {
      oil_price_usd_bbl: number
      steam_cost_usd_tonne: number
      opex_usd_day: number
      timeline: Record<string, unknown>[]
    }) => axios.post(`${BASE}/economics/analyse`, params).then(r => r.data),
  },

  risk: {
    score: (params: RiskRequest): Promise<RiskScore> =>
      axios.post(`${BASE}/risk/score`, params).then(r => r.data),
  },

  optimizer: {
    optimize: (req: OptimizerRequest): Promise<OptimizationResult> =>
      axios.post(`${BASE}/optimizer/optimize`, req).then(r => r.data),
  },
}
