import React from 'react'
import type { Economics, InjectionSummary } from '../types'

const fmt = (n: number, dec = 0) => n.toLocaleString('en-IN', { maximumFractionDigits: dec })
const usd = (n: number) => '$' + fmt(n, 0)

interface Props {
  economics: Economics
  injection: InjectionSummary
  cycleOil: number
  cycleSteam: number
  sor: number
}

export const EconomicsDashboard: React.FC<Props> = ({ economics: e, injection: inj, cycleOil, cycleSteam, sor }) => {
  const cards: { label: string; value: string; color?: string }[] = [
    { label: 'Total Oil', value: fmt(cycleOil) + ' bbl' },
    { label: 'Total Steam', value: fmt(cycleSteam) + ' t' },
    { label: 'SOR (t/bbl)', value: sor.toFixed(2) },
    { label: 'Heated Radius', value: inj.heated_radius_m.toFixed(1) + ' m' },
    { label: 'Thermal Efficiency', value: (inj.thermal_efficiency_indicator * 100).toFixed(1) + ' %' },
    { label: 'Gross Revenue', value: usd(e.gross_revenue_usd), color: '#27ae60' },
    { label: 'Steam Cost', value: usd((e.total_steam_t ?? 0) * 12), color: '#e74c3c' },
    { label: 'Net Cash Flow', value: usd(e.net_cash_flow_usd), color: e.net_cash_flow_usd >= 0 ? '#27ae60' : '#e74c3c' },
    { label: 'NPV', value: usd(e.npv_usd), color: e.npv_usd >= 0 ? '#2980b9' : '#e74c3c' },
    { label: 'Unit Cost', value: '$' + e.unit_cost_usd_bbl.toFixed(2) + '/bbl' },
    { label: 'Payout Day', value: e.payout_day ? `Day ${e.payout_day}` : 'Not achieved', color: e.payout_day ? '#27ae60' : '#e74c3c' },
    { label: 'Economic?', value: e.is_economic ? 'YES' : 'NO', color: e.is_economic ? '#27ae60' : '#e74c3c' },
  ]

  return (
    <div>
      <h3 style={{ marginBottom: 12, color: '#333' }}>Economics & Cycle Metrics</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 10 }}>
        {cards.map(c => (
          <div key={c.label} style={{
            background: '#f9f9f9', border: '1px solid #e0e0e0', borderRadius: 8,
            padding: '10px 12px', textAlign: 'center',
          }}>
            <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>{c.label}</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: c.color ?? '#333' }}>{c.value}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
