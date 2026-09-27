import React from 'react'
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import type { CandidatePlan } from '../types'

interface Props {
  allCandidates: CandidatePlan[]
  paretoCandidates: CandidatePlan[]
  currentPlan: CandidatePlan
  selectedPlan: CandidatePlan
}

interface ScatterPoint {
  x: number  // SOR
  y: number  // Cumulative Oil
  planId: string
  steamRate: number
  steamPressure: number
  injDays: number
  soakDays: number
  prodDays: number
  cumSteam: number
  category: 'Current Plan' | 'Selected Plan' | 'Pareto Optimal' | 'Feasible Candidate'
}

export const ParetoChart: React.FC<Props> = ({
  allCandidates,
  paretoCandidates,
  currentPlan,
  selectedPlan,
}) => {
  const paretoIds = new Set(paretoCandidates.map(c => c.plan_id))

  // Separate points by category for clean legend and distinct rendering
  const otherFeasibleData: ScatterPoint[] = []
  const paretoData: ScatterPoint[] = []
  const currentData: ScatterPoint[] = []
  const selectedData: ScatterPoint[] = []

  // Add all feasible candidates
  for (const c of allCandidates) {
    if (!c.is_feasible) continue

    const pt: ScatterPoint = {
      x: +c.sor_t_per_bbl.toFixed(3),
      y: +c.cumulative_oil_bbl.toFixed(0),
      planId: c.plan_id,
      steamRate: c.steam_rate_tpd,
      steamPressure: c.steam_pressure_bar,
      injDays: c.injection_days,
      soakDays: c.soak_days,
      prodDays: c.production_days,
      cumSteam: c.cumulative_steam_t,
      category: 'Feasible Candidate',
    }

    if (c.plan_id === currentPlan.plan_id) {
      pt.category = 'Current Plan'
      currentData.push(pt)
    } else if (c.plan_id === selectedPlan.plan_id) {
      pt.category = 'Selected Plan'
      selectedData.push(pt)
    } else if (paretoIds.has(c.plan_id)) {
      pt.category = 'Pareto Optimal'
      paretoData.push(pt)
    } else {
      otherFeasibleData.push(pt)
    }
  }

  // Ensure current and selected are present even if not in allCandidates list
  if (currentData.length === 0 && currentPlan.is_feasible) {
    currentData.push({
      x: +currentPlan.sor_t_per_bbl.toFixed(3),
      y: +currentPlan.cumulative_oil_bbl.toFixed(0),
      planId: currentPlan.plan_id,
      steamRate: currentPlan.steam_rate_tpd,
      steamPressure: currentPlan.steam_pressure_bar,
      injDays: currentPlan.injection_days,
      soakDays: currentPlan.soak_days,
      prodDays: currentPlan.production_days,
      cumSteam: currentPlan.cumulative_steam_t,
      category: 'Current Plan',
    })
  }

  if (selectedData.length === 0 && selectedPlan.is_feasible) {
    selectedData.push({
      x: +selectedPlan.sor_t_per_bbl.toFixed(3),
      y: +selectedPlan.cumulative_oil_bbl.toFixed(0),
      planId: selectedPlan.plan_id,
      steamRate: selectedPlan.steam_rate_tpd,
      steamPressure: selectedPlan.steam_pressure_bar,
      injDays: selectedPlan.injection_days,
      soakDays: selectedPlan.soak_days,
      prodDays: selectedPlan.production_days,
      cumSteam: selectedPlan.cumulative_steam_t,
      category: 'Selected Plan',
    })
  }

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload as ScatterPoint
      return (
        <div style={{
          background: 'rgba(255, 255, 255, 0.96)',
          border: '1px solid #ccc',
          borderRadius: 8,
          padding: '10px 14px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          fontSize: 12,
          color: '#333',
        }}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 4, color: '#1a2980' }}>
            {data.planId} ({data.category})
          </div>
          <div><strong>Cumulative Oil:</strong> {data.y.toLocaleString()} bbl</div>
          <div><strong>SOR:</strong> {data.x.toFixed(2)} t/bbl</div>
          <div><strong>Total Steam:</strong> {data.cumSteam.toLocaleString()} t</div>
          <div style={{ marginTop: 6, borderTop: '1px solid #eee', paddingTop: 4, color: '#666' }}>
            <span>Rate: {data.steamRate} t/d | Press: {data.steamPressure.toFixed(0)} bar</span>
            <br />
            <span>Inj: {data.injDays}d | Soak: {data.soakDays}d | Prod: {data.prodDays}d</span>
          </div>
        </div>
      )
    }
    return null
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
        <h4 style={{ margin: 0, color: '#2c3e50', fontSize: 14 }}>
          Pareto Trade-Off Frontier: Oil Production vs. Steam-to-Oil Ratio
        </h4>
        <span style={{ fontSize: 11, color: '#888' }}>
          Ideal = High Oil (Top) & Low SOR (Left)
        </span>
      </div>

      <ResponsiveContainer width="100%" height={340}>
        <ScatterChart margin={{ top: 15, right: 25, bottom: 25, left: 15 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e8e8e8" />
          <XAxis
            type="number"
            dataKey="x"
            name="SOR"
            unit=" t/bbl"
            label={{ value: 'Steam-to-Oil Ratio (t steam / bbl oil) — [Lower is Better]', position: 'insideBottom', offset: -15, fontSize: 12 }}
            domain={['auto', 'auto']}
          />
          <YAxis
            type="number"
            dataKey="y"
            name="Cumulative Oil"
            unit=" bbl"
            label={{ value: 'Cumulative Oil (bbl) — [Higher is Better]', angle: -90, position: 'insideLeft', offset: -5, fontSize: 12 }}
            domain={['auto', 'auto']}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: 12 }} />

          {/* Background Feasible Candidates */}
          <Scatter
            name="Feasible Candidates"
            data={otherFeasibleData}
            fill="#a0aec0"
            opacity={0.45}
            shape="circle"
          />

          {/* Pareto Optimal Front */}
          <Scatter
            name="Pareto Optimal Front"
            data={paretoData}
            fill="#0984e3"
            opacity={0.9}
            shape="circle"
          />

          {/* Current Operating Plan */}
          <Scatter
            name="Current Plan"
            data={currentData}
            fill="#e74c3c"
            shape="triangle"
          />

          {/* Selected Plan */}
          <Scatter
            name="Selected Plan"
            data={selectedData}
            fill="#00b894"
            shape="star"
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}
