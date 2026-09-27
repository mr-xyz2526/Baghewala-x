// Central TypeScript types mirroring backend Pydantic models

export type Phase = 'INJECTION' | 'SOAKING' | 'PRODUCTION'
export type Mode = 'SIMULATED_DEMO' | 'HISTORICAL' | 'FIELD_VALIDATED'

export interface CycleTimelineRecord {
  day: number
  phase: Phase
  temperature_c: number
  viscosity_cp: number
  oil_rate_bopd: number
  cumulative_oil_bbl: number
  steam_rate_tpd: number
  cumulative_steam_t: number
}

export interface InjectionSummary {
  heated_radius_m: number
  heated_area_m2: number
  total_heat_mj: number
  thermal_efficiency_indicator: number
}

export interface CycleResult {
  full_cycle_timeline: CycleTimelineRecord[]
  cycle_oil: number
  cycle_steam: number
  SOR: number
  sor_cwe_bbl_per_bbl: number
  temperature_history: number[]
  viscosity_history: number[]
  phase_boundaries: {
    injection: { start_day: number; end_day: number }
    soak: { start_day: number; end_day: number }
    production: { start_day: number; end_day: number }
  }
  injection_summary: InjectionSummary
}

export interface Economics {
  total_oil_bbl: number
  total_steam_t: number
  sor_t_per_bbl: number
  gross_revenue_usd: number
  net_cash_flow_usd: number
  npv_usd: number
  payout_day: number | null
  unit_cost_usd_bbl: number
  is_economic: boolean
}

export interface SRPPoint {
  spm: number
  stroke_length_in: number
  plunger_stroke_in: number
  pump_fillage_pct: number
  theoretical_fluid_bpd: number
  peak_rod_load_lbf: number
  min_rod_load_lbf: number
  rod_stress_indicator: number
  motor_power_kw: number
  torque_indicator_ft_lbf: number
  fluid_load_lbf: number
  oil_rate_bopd: number
}

export interface RiskScore {
  anomaly_class: string
  anomaly_probability: number
  rod_floating_risk: number
  impact_risk: number
  equipment_risk: number
  flags: string[]
  recommendations: string[]
}

export interface TwinRunResult {
  well_id: string
  cycle_result: CycleResult
  economics: Economics
  srp_point: SRPPoint
  risk_score: RiskScore
  final_well_state: Record<string, unknown>
  history_count: number
}

export interface TwinRunRequest {
  well_id?: string
  well_name?: string
  field_name?: string
  steam_rate_tpd?: number
  steam_temp_c?: number
  injection_days?: number
  steam_quality?: number
  soak_days?: number
  production_days?: number
  spm?: number
  vfd_hz?: number
  water_cut_pct?: number
  oil_price_usd_bbl?: number
  steam_cost_usd_tonne?: number
}

// ── Optimization Types ────────────────────────────────────────────────────────

export interface CandidatePlan {
  plan_id: string
  steam_rate_tpd: number
  steam_pressure_bar: number
  steam_temp_c: number
  injection_days: number
  soak_days: number
  production_days: number
  cumulative_oil_bbl: number
  sor_t_per_bbl: number
  cumulative_steam_t: number
  heated_radius_m: number
  thermal_efficiency: number
  final_oil_rate_bopd: number
  is_feasible: boolean
  constraint_violations: string[]
  pareto_rank: number
  crowding_distance: number
}

export interface AlternativePlanRow {
  strategy: string
  plan_id: string
  steam_rate_tpd: number
  steam_pressure_bar: number
  injection_days: number
  soak_days: number
  production_days: number
  cumulative_oil_bbl: number
  sor_t_per_bbl: number
  cumulative_steam_t: number
  heated_radius_m: number
  oil_delta_vs_current_bbl: number
  sor_delta_vs_current: number
  steam_delta_vs_current_t: number
}

export interface OptimizationResult {
  pareto_candidates: CandidatePlan[]
  current_plan: CandidatePlan
  selected_plan: CandidatePlan
  selection_rule_description: string
  objective_values: {
    current_plan: Record<string, number>
    selected_plan: Record<string, number>
    pareto_front_size: number
  }
  constraints_summary: {
    total_evaluated: number
    feasible_candidates: number
    infeasible_candidates: number
    feasibility_rate_pct: number
  }
  alternatives_table: AlternativePlanRow[]
  explanation_of_trade_offs: string
  all_evaluated_candidates: CandidatePlan[]
}

export interface OptimizerRequest {
  current_plan?: Partial<CandidatePlan>
  bounds?: Record<string, number>
  selection_rule?: {
    rule_name: string
    weight_oil: number
    weight_sor: number
    weight_steam: number
  }
  use_nsga2?: boolean
  random_seed?: number
}
