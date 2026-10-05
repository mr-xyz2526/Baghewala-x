import React, { useState, useMemo } from 'react'
import type { TwinRunResult, WhatIfScenario, WhatIfDayResult, RiskLevel } from '../types'
import type { NavScreen } from '../App'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts'

interface SharedProps {
  twinResult: TwinRunResult | null
  twinLoading: boolean
  twinParams: any
  setTwinParams: (p: any) => void
  runTwin: (params?: any) => void
  setScreen: (s: NavScreen) => void
}

const DEFAULTS: WhatIfScenario = {
  spm: 6.0,
  vfd_hz: 36,
  stroke_in: 72,
  steam_rate_tpd: 800,
  soak_days: 4,
}

// Simulate 7-day evolution given scenario parameters
function simulateWhatIf(scenario: WhatIfScenario, baseVisc: number, baseTemp: number): WhatIfDayResult[] {
  const days: WhatIfDayResult[] = []
  for (let day = 0; day <= 7; day++) {
    const cooling = Math.exp(-day * 0.04)
    const temp = baseTemp * cooling + 80 * (1 - cooling)
    // Viscosity is inversely related to temperature (simplified Andrade model)
    const viscFactor = Math.exp(2000 * (1 / (temp + 273.15) - 1 / (baseTemp + 273.15)))
    const visc = Math.min(8000, baseVisc * viscFactor)

    // Fillage depends on viscosity and SPM
    const viscImpact = Math.max(0, (visc - 500) / 5000)
    const fillage = Math.max(20, Math.min(100, 90 - viscImpact * 60 - (scenario.spm - 5) * 3))

    // Oil rate
    const fluidRate = scenario.spm * scenario.stroke_in * 0.0119  // theoretical BFPD
    const oil = Math.max(0, fluidRate * (fillage / 100) * 0.7)  // with water cut ~30%

    // Power
    const power = scenario.spm * scenario.stroke_in * 0.005 * (1 + viscImpact * 0.4)

    // Risk
    let risk: RiskLevel = 'NORMAL'
    if (fillage < 50) risk = 'CRITICAL'
    else if (fillage < 65) risk = 'HIGH'
    else if (visc > 3000 || fillage < 75) risk = 'WARNING'

    days.push({
      day,
      temperature_c: +temp.toFixed(1),
      viscosity_cp: +visc.toFixed(0),
      oil_rate_bopd: +oil.toFixed(1),
      sor: +(scenario.steam_rate_tpd / Math.max(1, oil)).toFixed(2),
      power_kw: +power.toFixed(1),
      fillage_pct: +fillage.toFixed(1),
      rod_load_lbf: +(10000 + viscImpact * 4000).toFixed(0),
      risk_level: risk,
    })
  }
  return days
}

function SliderField({ label, value, min, max, step, unit, color, onChange }: {
  label: string; value: number; min: number; max: number; step: number; unit: string; color?: string
  onChange: (v: number) => void
}) {
  return (
    <div className="form-group" style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
        <label className="form-label">{label}</label>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600, color: color ?? 'var(--text-bright)' }}>
          {value} {unit}
        </span>
      </div>
      <input type="range" className="form-slider" min={min} max={max} step={step} value={value}
        onChange={e => onChange(Number(e.target.value))} />
    </div>
  )
}

function RiskPill({ level }: { level: RiskLevel }) {
  const colors: Record<RiskLevel, string> = {
    NORMAL: 'var(--green)', WARNING: 'var(--amber)', HIGH: 'var(--orange)', CRITICAL: 'var(--red)',
  }
  return (
    <span style={{
      background: colors[level] + '22', color: colors[level],
      border: `1px solid ${colors[level]}44`,
      borderRadius: 100, padding: '2px 8px', fontSize: 9, fontWeight: 700, letterSpacing: '0.06em',
    }}>{level}</span>
  )
}

export function WhatIfPage({ twinResult }: SharedProps) {
  const [current, setCurrent] = useState<WhatIfScenario>(DEFAULTS)
  const [scenario, setScenario] = useState<WhatIfScenario>({ ...DEFAULTS, spm: 4.5, vfd_hz: 27 })
  const [optimized] = useState<WhatIfScenario>({ spm: 5.5, vfd_hz: 33, stroke_in: 72, steam_rate_tpd: 900, soak_days: 5 })
  const [simulating, setSimulating] = useState(false)
  const [simulated, setSimulated] = useState(false)

  const baseVisc = twinResult?.cycle_result.full_cycle_timeline.slice(-1)[0]?.viscosity_cp ?? 850
  const baseTemp = twinResult?.cycle_result.full_cycle_timeline.slice(-1)[0]?.temperature_c ?? 155

  const currentDays  = useMemo(() => simulateWhatIf(current, baseVisc, baseTemp), [current, baseVisc, baseTemp])
  const scenarioDays = useMemo(() => simulateWhatIf(scenario, baseVisc, baseTemp), [scenario, baseVisc, baseTemp])
  const optimizedDays = useMemo(() => simulateWhatIf(optimized, baseVisc, baseTemp), [optimized, baseVisc, baseTemp])

  const simulate7Days = () => {
    setSimulating(true)
    setTimeout(() => {
      setSimulating(false)
      setSimulated(true)
    }, 1200)
  }

  const setScen = (k: keyof WhatIfScenario) => (v: number) => setScenario(p => ({ ...p, [k]: v }))
  const setCurr = (k: keyof WhatIfScenario) => (v: number) => setCurrent(p => ({ ...p, [k]: v }))

  const lastCurrent  = currentDays[7]
  const lastScenario = scenarioDays[7]
  const lastOptimized = optimizedDays[7]

  const mergedData = currentDays.map((c, i) => ({
    day: c.day,
    curr_oil: c.oil_rate_bopd,
    scen_oil: scenarioDays[i].oil_rate_bopd,
    opt_oil: optimizedDays[i].oil_rate_bopd,
    curr_visc: c.viscosity_cp,
    scen_visc: scenarioDays[i].viscosity_cp,
    opt_visc: optimizedDays[i].viscosity_cp,
    curr_fillage: c.fillage_pct,
    scen_fillage: scenarioDays[i].fillage_pct,
    opt_fillage: optimizedDays[i].fillage_pct,
  }))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: 18, margin: 0 }}>WHAT-IF SIMULATOR</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 12, margin: '4px 0 0' }}>
            7-Day forward simulation · Parametric scenario comparison · Demo model
          </p>
        </div>
        <button
          className="btn btn-primary btn-lg"
          onClick={simulate7Days}
          disabled={simulating}
        >
          {simulating ? <><span className="spinner" /> SIMULATING…</> : '▶ SIMULATE 7 DAYS'}
        </button>
      </div>

      {/* 3-column scenario comparison */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14 }}>

        {/* CURRENT */}
        <div className="panel" style={{ borderColor: 'var(--border)' }}>
          <div className="panel-header">
            <div className="panel-title" style={{ color: 'var(--text-muted)' }}>CURRENT</div>
            <div className="risk-badge normal">BASELINE</div>
          </div>
          <SliderField label="SPM" value={current.spm} min={2} max={12} step={0.5} unit="spm" onChange={setCurr('spm')} />
          <SliderField label="VFD" value={current.vfd_hz} min={20} max={60} step={1} unit="Hz" color="var(--amber)" onChange={setCurr('vfd_hz')} />
          <SliderField label="Stroke" value={current.stroke_in} min={48} max={96} step={6} unit="in" onChange={setCurr('stroke_in')} />
          <SliderField label="Steam Rate" value={current.steam_rate_tpd} min={400} max={1200} step={50} unit="t/d" color="var(--amber)" onChange={setCurr('steam_rate_tpd')} />
          <SliderField label="Soak Days" value={current.soak_days} min={2} max={10} step={1} unit="d" onChange={setCurr('soak_days')} />
          <hr className="divider" />
          <div className="telem-grid">
            <div className="telem-item"><div className="telem-label">OIL RATE</div><div className="telem-value green">{lastCurrent.oil_rate_bopd.toFixed(0)}</div><div style={{ fontSize: 9, color: 'var(--text-muted)' }}>BOPD @ Day 7</div></div>
            <div className="telem-item"><div className="telem-label">VISCOSITY</div><div className="telem-value cyan">{lastCurrent.viscosity_cp.toFixed(0)}</div><div style={{ fontSize: 9, color: 'var(--text-muted)' }}>cP @ Day 7</div></div>
            <div className="telem-item"><div className="telem-label">FILLAGE</div><div className="telem-value" style={{ color: lastCurrent.fillage_pct < 65 ? 'var(--red)' : 'var(--green)' }}>{lastCurrent.fillage_pct.toFixed(0)}%</div></div>
            <div className="telem-item"><div className="telem-label">RISK</div><RiskPill level={lastCurrent.risk_level} /></div>
          </div>
        </div>

        {/* SCENARIO */}
        <div className="panel" style={{ borderColor: 'var(--amber)', boxShadow: '0 0 12px rgba(245,158,11,0.08)' }}>
          <div className="panel-header">
            <div className="panel-title" style={{ color: 'var(--amber)' }}>SCENARIO</div>
            <div className="risk-badge warning">MODIFIED</div>
          </div>
          <SliderField label="SPM" value={scenario.spm} min={2} max={12} step={0.5} unit="spm" onChange={setScen('spm')} />
          <SliderField label="VFD" value={scenario.vfd_hz} min={20} max={60} step={1} unit="Hz" color="var(--amber)" onChange={setScen('vfd_hz')} />
          <SliderField label="Stroke" value={scenario.stroke_in} min={48} max={96} step={6} unit="in" onChange={setScen('stroke_in')} />
          <SliderField label="Steam Rate" value={scenario.steam_rate_tpd} min={400} max={1200} step={50} unit="t/d" color="var(--amber)" onChange={setScen('steam_rate_tpd')} />
          <SliderField label="Soak Days" value={scenario.soak_days} min={2} max={10} step={1} unit="d" onChange={setScen('soak_days')} />
          <hr className="divider" />
          <div className="telem-grid">
            <div className="telem-item"><div className="telem-label">OIL RATE</div>
              <div className="telem-value" style={{ color: lastScenario.oil_rate_bopd > lastCurrent.oil_rate_bopd ? 'var(--green)' : 'var(--red)' }}>
                {lastScenario.oil_rate_bopd.toFixed(0)}
              </div>
              <div style={{ fontSize: 9, color: lastScenario.oil_rate_bopd > lastCurrent.oil_rate_bopd ? 'var(--green)' : 'var(--red)' }}>
                {lastScenario.oil_rate_bopd > lastCurrent.oil_rate_bopd ? '▲' : '▼'}{' '}
                {Math.abs(lastScenario.oil_rate_bopd - lastCurrent.oil_rate_bopd).toFixed(0)} vs current
              </div>
            </div>
            <div className="telem-item"><div className="telem-label">VISCOSITY</div><div className="telem-value cyan">{lastScenario.viscosity_cp.toFixed(0)}</div><div style={{ fontSize: 9, color: 'var(--text-muted)' }}>cP @ Day 7</div></div>
            <div className="telem-item"><div className="telem-label">FILLAGE</div><div className="telem-value" style={{ color: lastScenario.fillage_pct < 65 ? 'var(--red)' : 'var(--green)' }}>{lastScenario.fillage_pct.toFixed(0)}%</div></div>
            <div className="telem-item"><div className="telem-label">RISK</div><RiskPill level={lastScenario.risk_level} /></div>
          </div>
        </div>

        {/* OPTIMIZED */}
        <div className="panel" style={{ borderColor: 'var(--cyan)', boxShadow: '0 0 12px rgba(6,182,212,0.08)' }}>
          <div className="panel-header">
            <div className="panel-title" style={{ color: 'var(--cyan)' }}>OPTIMIZED</div>
            <div className="risk-badge normal">RECOMMENDED</div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
            {[
              { label: 'SPM', value: optimized.spm.toFixed(1), unit: 'spm', color: '' },
              { label: 'VFD', value: optimized.vfd_hz.toString(), unit: 'Hz', color: 'amber' },
              { label: 'STROKE', value: optimized.stroke_in.toString(), unit: 'in', color: '' },
              { label: 'STEAM', value: optimized.steam_rate_tpd.toString(), unit: 't/d', color: 'amber' },
              { label: 'SOAK', value: optimized.soak_days.toString(), unit: 'd', color: '' },
            ].map(item => (
              <div key={item.label} className="panel-card">
                <div className="telem-label">{item.label}</div>
                <div className={`telem-value ${item.color}`} style={{ fontSize: 14 }}>{item.value} <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>{item.unit}</span></div>
              </div>
            ))}
          </div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 8, lineHeight: 1.4 }}>
            From optimizer — balanced compromise selection. See OPTIMIZE screen.
          </div>
          <hr className="divider" />
          <div className="telem-grid">
            <div className="telem-item"><div className="telem-label">OIL RATE</div>
              <div className="telem-value green">{lastOptimized.oil_rate_bopd.toFixed(0)}</div>
              <div style={{ fontSize: 9, color: 'var(--green)' }}>▲ {Math.abs(lastOptimized.oil_rate_bopd - lastCurrent.oil_rate_bopd).toFixed(0)} vs current</div>
            </div>
            <div className="telem-item"><div className="telem-label">VISCOSITY</div><div className="telem-value cyan">{lastOptimized.viscosity_cp.toFixed(0)}</div></div>
            <div className="telem-item"><div className="telem-label">FILLAGE</div><div className="telem-value green">{lastOptimized.fillage_pct.toFixed(0)}%</div></div>
            <div className="telem-item"><div className="telem-label">RISK</div><RiskPill level={lastOptimized.risk_level} /></div>
          </div>
        </div>
      </div>

      {/* 7-day evolution charts */}
      {(simulated || true) && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">7-DAY OIL RATE EVOLUTION</div>
              <div className="label-sm">CURRENT vs SCENARIO vs OPTIMIZED</div>
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={mergedData} margin={{ top: 5, right: 20, bottom: 20, left: 10 }}>
                <CartesianGrid strokeDasharray="2 4" stroke="var(--border-dim)" />
                <XAxis dataKey="day" tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                  label={{ value: 'Day', position: 'insideBottomRight', offset: -5, fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                  label={{ value: 'Oil Rate (BOPD)', angle: -90, position: 'insideLeft', fontSize: 10, fill: 'var(--text-muted)' }} />
                <Tooltip contentStyle={{ background: 'var(--bg-panel)', border: '1px solid var(--border-hi)', borderRadius: 6, fontSize: 11 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line dataKey="curr_oil" name="Current" stroke="var(--text-muted)" dot={false} strokeWidth={1.5} strokeDasharray="4 2" />
                <Line dataKey="scen_oil" name="Scenario" stroke="var(--amber)" dot={false} strokeWidth={2} />
                <Line dataKey="opt_oil" name="Optimized" stroke="var(--green)" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="panel">
              <div className="panel-header"><div className="panel-title">VISCOSITY EVOLUTION (cP)</div></div>
              <ResponsiveContainer width="100%" height={160}>
                <LineChart data={mergedData} margin={{ top: 5, right: 20, bottom: 20, left: 10 }}>
                  <CartesianGrid strokeDasharray="2 4" stroke="var(--border-dim)" />
                  <XAxis dataKey="day" tick={{ fill: 'var(--text-muted)', fontSize: 9, fontFamily: 'var(--font-mono)' }} />
                  <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 9, fontFamily: 'var(--font-mono)' }} />
                  <Tooltip contentStyle={{ background: 'var(--bg-panel)', border: '1px solid var(--border-hi)', borderRadius: 6, fontSize: 11 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line dataKey="curr_visc" name="Current" stroke="var(--text-muted)" dot={false} strokeWidth={1.5} strokeDasharray="4 2" />
                  <Line dataKey="scen_visc" name="Scenario" stroke="var(--amber)" dot={false} strokeWidth={2} />
                  <Line dataKey="opt_visc" name="Optimized" stroke="var(--cyan)" dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="panel">
              <div className="panel-header"><div className="panel-title">PUMP FILLAGE EVOLUTION (%)</div></div>
              <ResponsiveContainer width="100%" height={160}>
                <LineChart data={mergedData} margin={{ top: 5, right: 20, bottom: 20, left: 10 }}>
                  <CartesianGrid strokeDasharray="2 4" stroke="var(--border-dim)" />
                  <XAxis dataKey="day" tick={{ fill: 'var(--text-muted)', fontSize: 9, fontFamily: 'var(--font-mono)' }} />
                  <YAxis domain={[0, 100]} tick={{ fill: 'var(--text-muted)', fontSize: 9, fontFamily: 'var(--font-mono)' }} />
                  <Tooltip contentStyle={{ background: 'var(--bg-panel)', border: '1px solid var(--border-hi)', borderRadius: 6, fontSize: 11 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line dataKey="curr_fillage" name="Current" stroke="var(--text-muted)" dot={false} strokeWidth={1.5} strokeDasharray="4 2" />
                  <Line dataKey="scen_fillage" name="Scenario" stroke="var(--amber)" dot={false} strokeWidth={2} />
                  <Line dataKey="opt_fillage" name="Optimized" stroke="var(--green)" dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* Explainability */}
      <div className="explain-block">
        <div className="explain-label">WHAT-IF MODEL NOTE</div>
        <div className="explain-text">
          7-day forward simulation uses a simplified thermal cooling model (exponential decay) combined
          with an Andrade-type viscosity correlation. Pump fillage responds to viscosity and SPM changes.
          Oil rate is estimated from pump geometry. These are demo projections — not calibrated field forecasts.
        </div>
      </div>
    </div>
  )
}
