import React, { useState } from 'react'
import type { TwinRunRequest } from '../types'

interface Props {
  defaults: TwinRunRequest
  onRun: (params: TwinRunRequest) => void
  loading: boolean
}

const field = (label: string, key: keyof TwinRunRequest, value: number | string,
  onChange: (k: keyof TwinRunRequest, v: number | string) => void,
  type: 'number' | 'text' = 'number', step = '1'
) => (
  <label style={{ display: 'flex', flexDirection: 'column', gap: 3, fontSize: 13 }}>
    <span style={{ color: '#555' }}>{label}</span>
    <input
      type={type} step={step} value={value}
      style={{ padding: '5px 8px', borderRadius: 6, border: '1px solid #ccc', width: '100%' }}
      onChange={e => onChange(key, type === 'number' ? Number(e.target.value) : e.target.value)}
    />
  </label>
)

export const ControlPanel: React.FC<Props> = ({ defaults, onRun, loading }) => {
  const [params, setParams] = useState<TwinRunRequest>(defaults)

  const set = (k: keyof TwinRunRequest, v: number | string) =>
    setParams(p => ({ ...p, [k]: v }))

  return (
    <div style={{ background: '#f4f6fb', borderRadius: 10, padding: 18, border: '1px solid #dde' }}>
      <h3 style={{ margin: '0 0 14px', color: '#2c3e50', fontSize: 15 }}>Simulation Controls</h3>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        {field('Steam Rate (t/d)', 'steam_rate_tpd', params.steam_rate_tpd ?? 800, set, 'number', '50')}
        {field('Steam Temp (°C)', 'steam_temp_c', params.steam_temp_c ?? 260, set, 'number', '10')}
        {field('Steam Quality (0-1)', 'steam_quality', params.steam_quality ?? 0.8, set, 'number', '0.05')}
        {field('Injection Days', 'injection_days', params.injection_days ?? 18, set)}
        {field('Soak Days', 'soak_days', params.soak_days ?? 4, set)}
        {field('Production Days', 'production_days', params.production_days ?? 70, set)}
        {field('SPM', 'spm', params.spm ?? 6, set, 'number', '0.5')}
        {field('Water Cut (%)', 'water_cut_pct', params.water_cut_pct ?? 30, set, 'number', '5')}
        {field('Oil Price (USD/bbl)', 'oil_price_usd_bbl', params.oil_price_usd_bbl ?? 60, set, 'number', '5')}
        {field('Steam Cost (USD/t)', 'steam_cost_usd_tonne', params.steam_cost_usd_tonne ?? 12, set, 'number', '1')}
      </div>

      <button
        onClick={() => onRun(params)}
        disabled={loading}
        style={{
          marginTop: 16, width: '100%', padding: '10px 0', background: loading ? '#aaa' : '#2980b9',
          color: '#fff', border: 'none', borderRadius: 8, cursor: loading ? 'not-allowed' : 'pointer',
          fontWeight: 700, fontSize: 14,
        }}
      >
        {loading ? 'Running…' : 'Run Twin Simulation'}
      </button>
    </div>
  )
}
