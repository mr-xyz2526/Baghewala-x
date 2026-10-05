import React, { useState } from 'react'
import type { TwinRunResult, CycleResult } from '../types'
import type { NavScreen } from '../App'
import { api } from '../api/client'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceArea,
} from 'recharts'

interface SharedProps {
  twinResult: TwinRunResult | null
  twinLoading: boolean
  twinParams: any
  setTwinParams: (p: any) => void
  runTwin: (params?: any) => void
  setScreen: (s: NavScreen) => void
}

interface CSSFormParams {
  steam_rate_tpd: number
  steam_temp_c: number
  steam_quality: number
  soak_days: number
  injection_days: number
  production_days: number
  base_drawdown_bar: number
  water_cut_pct: number
}

const DEFAULTS: CSSFormParams = {
  steam_rate_tpd: 800,
  steam_temp_c: 260,
  steam_quality: 0.80,
  soak_days: 4,
  injection_days: 18,
  production_days: 70,
  base_drawdown_bar: 20,
  water_cut_pct: 30,
}

function SliderField({ label, value, min, max, step, unit, onChange, color = '' }: {
  label: string; value: number; min: number; max: number; step: number; unit: string
  onChange: (v: number) => void; color?: string
}) {
  return (
    <div className="form-group" style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <label className="form-label">{label}</label>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: color || 'var(--text-bright)', fontWeight: 600 }}>
          {value} {unit}
        </span>
      </div>
      <input
        type="range" className="form-slider"
        min={min} max={max} step={step} value={value}
        onChange={e => onChange(Number(e.target.value))}
      />
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: 'var(--text-label)' }}>
        <span>{min}</span><span>{max}</span>
      </div>
    </div>
  )
}

// Animated thermal visualization
function ThermalVisualization({ heatedRadius, tempC, isInjecting }: {
  heatedRadius: number; tempC: number; isInjecting: boolean
}) {
  const scale = Math.min(1.0, heatedRadius / 40)
  const maxR = 110

  return (
    <svg viewBox="0 0 280 200" width="100%" style={{ background: 'var(--bg-input)', borderRadius: 6, border: '1px solid var(--border)' }}>
      <rect x="0" y="0" width="280" height="200" fill="#080c18" />

      {/* Concentric heat rings */}
      {[1.0, 0.75, 0.5, 0.3].map((factor, i) => (
        <ellipse key={i}
          cx="140" cy="140"
          rx={maxR * scale * factor}
          ry={maxR * scale * factor * 0.35}
          fill={`rgba(${i === 0 ? '245,158,11' : i === 1 ? '249,115,22' : i === 2 ? '239,68,68' : '220,38,38'}, ${0.06 + i * 0.04})`}
          stroke={`rgba(${i === 0 ? '245,158,11' : i === 1 ? '249,115,22' : i === 2 ? '239,68,68' : '220,38,38'}, ${0.2 + i * 0.1})`}
          strokeWidth="0.5"
          className={i === 0 ? 'thermal-ring' : ''}
        />
      ))}

      {/* Injection point */}
      <line x1="140" y1="10" x2="140" y2="140" stroke="var(--cyan)" strokeWidth="1" strokeDasharray="3 3" opacity="0.5" />
      <circle cx="140" cy="140" r="4" fill="var(--red)" />

      {/* Steam arrows (when injecting) */}
      {isInjecting && [130, 140, 150].map((x, i) => (
        <g key={x} style={{ animation: `steam-rise ${1.5 + i * 0.3}s ease-out ${i * 0.2}s infinite` }}>
          <ellipse cx={x} cy={80 - i * 10} rx="3" ry="2" fill="rgba(245,158,11,0.5)" />
        </g>
      ))}

      {/* Labels */}
      <text x="10" y="20" fontSize="9" fill="var(--amber)" fontFamily="var(--font-mono)">HEATED RADIUS: {heatedRadius.toFixed(1)} m</text>
      <text x="10" y="32" fontSize="9" fill="var(--text-muted)" fontFamily="var(--font-mono)">STEAM TEMP: {tempC}°C</text>

      {/* Temperature legend */}
      <text x="220" y="100" fontSize="8" fill="var(--red)" fontFamily="var(--font-mono)">{tempC}°C</text>
      <text x="220" y="120" fontSize="8" fill="var(--orange)" fontFamily="var(--font-mono)">{Math.round(tempC * 0.8)}°C</text>
      <text x="220" y="140" fontSize="8" fill="var(--amber)" fontFamily="var(--font-mono)">{Math.round(tempC * 0.6)}°C</text>
      <text x="220" y="160" fontSize="8" fill="var(--text-muted)" fontFamily="var(--font-mono)">AMBIENT</text>

      <text x="140" y="195" textAnchor="middle" fontSize="8" fill="var(--text-label)" fontFamily="var(--font-mono)">
        RESERVOIR CROSS-SECTION (TOP VIEW)
      </text>
    </svg>
  )
}

export function CSSPage({ twinResult, twinParams, setScreen }: SharedProps) {
  const [params, setParams] = useState<CSSFormParams>(DEFAULTS)
  const [cssResult, setCssResult] = useState<CycleResult | null>(twinResult?.cycle_result ?? null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const set = (k: keyof CSSFormParams) => (v: number) => setParams(p => ({ ...p, [k]: v }))

  const runScenario = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.css.run({
        steam_rate_tpd: params.steam_rate_tpd,
        steam_temp_c: params.steam_temp_c,
        steam_quality: params.steam_quality,
        soak_days: params.soak_days,
        injection_days: params.injection_days,
        production_days: params.production_days,
        water_cut_pct: params.water_cut_pct,
      })
      setCssResult(result)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'CSS run failed')
    } finally {
      setLoading(false)
    }
  }

  const timeline = cssResult?.full_cycle_timeline ?? []
  const pb = cssResult?.phase_boundaries
  const inj = cssResult?.injection_summary
  const lastRecord = timeline.slice(-1)[0]
  const finalTemp = lastRecord?.temperature_c ?? 120
  const finalVisc = lastRecord?.viscosity_cp ?? 850

  const chartData = timeline.map(r => ({
    day: r.day,
    temp: +r.temperature_c.toFixed(1),
    visc: +r.viscosity_cp.toFixed(0),
    oil:  +r.oil_rate_bopd.toFixed(1),
    steam: +r.steam_rate_tpd.toFixed(0),
  }))

  const sorColor = (cssResult?.SOR ?? 5) > 7 ? 'red' : (cssResult?.SOR ?? 5) > 5 ? 'orange' : 'green'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: 18, margin: 0 }}>CSS STUDIO</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 12, margin: '4px 0 0' }}>
            Cyclic Steam Stimulation · Marx-Langenheim Thermal Model · Synthetic Demo
          </p>
        </div>
        {error && <div className="alert alert-danger" style={{ margin: 0, padding: '6px 12px' }}>{error}</div>}
      </div>

      {/* Main 3-column grid */}
      <div className="grid-3col">

        {/* LEFT: Controls */}
        <div className="panel" style={{ position: 'sticky', top: 70 }}>
          <div className="panel-header">
            <div className="panel-title">INJECTION CONTROLS</div>
          </div>

          {/* CSS cycle timeline */}
          <div style={{ marginBottom: 14 }}>
            <div className="label-sm" style={{ marginBottom: 6 }}>CYCLE SCHEDULE</div>
            <div className="cycle-timeline">
              <div className="cycle-phase injection" style={{ flex: params.injection_days }}>
                INJ {params.injection_days}d
              </div>
              <div className="cycle-phase soak" style={{ flex: params.soak_days }}>
                SOAK {params.soak_days}d
              </div>
              <div className="cycle-phase production" style={{ flex: Math.min(params.production_days, 80) }}>
                PROD {params.production_days}d
              </div>
            </div>
          </div>

          <SliderField label="Steam Rate" value={params.steam_rate_tpd} min={400} max={1200} step={50} unit="t/d" onChange={set('steam_rate_tpd')} color="var(--amber)" />
          <SliderField label="Steam Temperature" value={params.steam_temp_c} min={200} max={320} step={10} unit="°C" onChange={set('steam_temp_c')} color="var(--amber)" />
          <SliderField label="Steam Quality" value={params.steam_quality} min={0.50} max={0.95} step={0.05} unit="" onChange={set('steam_quality')} />
          <SliderField label="Injection Days" value={params.injection_days} min={10} max={30} step={1} unit="d" onChange={set('injection_days')} />
          <SliderField label="Soak Duration" value={params.soak_days} min={2} max={10} step={1} unit="d" onChange={set('soak_days')} />
          <SliderField label="Production Days" value={params.production_days} min={40} max={120} step={5} unit="d" onChange={set('production_days')} />
          <SliderField label="Water Cut" value={params.water_cut_pct} min={10} max={70} step={5} unit="%" onChange={set('water_cut_pct')} />

          <button
            className="btn btn-amber btn-lg"
            style={{ width: '100%', marginTop: 4 }}
            onClick={runScenario}
            disabled={loading}
          >
            {loading ? <><span className="spinner" /> RUNNING…</> : '♨ RUN SCENARIO'}
          </button>
        </div>

        {/* CENTER: Thermal visualization + charts */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">THERMAL PROFILE</div>
              <div className="label-sm">
                HEATED RADIUS: {(inj?.heated_radius_m ?? 28).toFixed(1)} m
              </div>
            </div>
            <ThermalVisualization
              heatedRadius={inj?.heated_radius_m ?? 28}
              tempC={params.steam_temp_c}
              isInjecting={true}
            />
          </div>

          {/* Temp + Viscosity chart */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">TEMPERATURE & VISCOSITY EVOLUTION</div>
            </div>
            {pb && (
              <div className="cycle-timeline" style={{ marginBottom: 8 }}>
                <div className="cycle-phase injection" style={{ flex: pb.injection.end_day - pb.injection.start_day }}>
                  INJ
                </div>
                <div className="cycle-phase soak" style={{ flex: pb.soak.end_day - pb.soak.start_day }}>
                  SOAK
                </div>
                <div className="cycle-phase production" style={{ flex: Math.min(pb.production.end_day - pb.production.start_day, 60) }}>
                  PRODUCTION
                </div>
              </div>
            )}
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartData} margin={{ top: 5, right: 25, bottom: 5, left: 10 }}>
                <CartesianGrid strokeDasharray="2 4" stroke="var(--border-dim)" />
                <XAxis dataKey="day" tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                  label={{ value: 'Day', position: 'insideBottomRight', offset: -5, fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis yAxisId="l" tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                  label={{ value: 'Temp (°C)', angle: -90, position: 'insideLeft', fontSize: 10, fill: 'var(--amber)' }} />
                <YAxis yAxisId="r" orientation="right" scale="log" domain={['auto', 'auto']}
                  tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                  label={{ value: 'Visc (cP)', angle: 90, position: 'insideRight', fontSize: 10, fill: 'var(--cyan)' }} />
                <Tooltip contentStyle={{ background: 'var(--bg-panel)', border: '1px solid var(--border-hi)', borderRadius: 6, fontSize: 11 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                {pb && <>
                  <ReferenceArea yAxisId="l" x1={pb.injection.start_day} x2={pb.injection.end_day} fill="rgba(245,158,11,0.08)" />
                  <ReferenceArea yAxisId="l" x1={pb.soak.start_day} x2={pb.soak.end_day} fill="rgba(139,92,246,0.08)" />
                  <ReferenceArea yAxisId="l" x1={pb.production.start_day} x2={pb.production.end_day} fill="rgba(16,185,129,0.06)" />
                </>}
                <Line yAxisId="l" dataKey="temp" name="Temp (°C)" stroke="var(--amber)" dot={false} strokeWidth={2} />
                <Line yAxisId="r" dataKey="visc" name="Viscosity (cP)" stroke="var(--cyan)" dot={false} strokeWidth={2} strokeDasharray="5 2" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Oil + Steam chart */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">OIL RATE & STEAM INJECTION</div>
            </div>
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={chartData} margin={{ top: 5, right: 25, bottom: 5, left: 10 }}>
                <CartesianGrid strokeDasharray="2 4" stroke="var(--border-dim)" />
                <XAxis dataKey="day" tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }} />
                <YAxis yAxisId="l" tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                  label={{ value: 'Oil (BOPD)', angle: -90, position: 'insideLeft', fontSize: 10, fill: 'var(--green)' }} />
                <YAxis yAxisId="r" orientation="right"
                  tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                  label={{ value: 'Steam (t/d)', angle: 90, position: 'insideRight', fontSize: 10, fill: 'var(--amber)' }} />
                <Tooltip contentStyle={{ background: 'var(--bg-panel)', border: '1px solid var(--border-hi)', borderRadius: 6, fontSize: 11 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                {pb && <>
                  <ReferenceArea yAxisId="l" x1={pb.injection.start_day} x2={pb.injection.end_day} fill="rgba(245,158,11,0.08)" />
                  <ReferenceArea yAxisId="l" x1={pb.soak.start_day} x2={pb.soak.end_day} fill="rgba(139,92,246,0.08)" />
                </>}
                <Line yAxisId="l" dataKey="oil" name="Oil (BOPD)" stroke="var(--green)" dot={false} strokeWidth={2} />
                <Line yAxisId="r" dataKey="steam" name="Steam (t/d)" stroke="var(--amber)" dot={false} strokeWidth={2} strokeDasharray="5 2" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* RIGHT: KPIs */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">CYCLE KPIs</div>
            </div>
            {[
              { label: 'PEAK TEMP', value: (cssResult ? Math.max(...timeline.map(r => r.temperature_c)) : params.steam_temp_c * 0.95).toFixed(1), unit: '°C', color: 'amber' },
              { label: 'FINAL VISCOSITY', value: finalVisc.toFixed(0), unit: 'cP', color: 'cyan' },
              { label: 'HEATED RADIUS', value: (inj?.heated_radius_m ?? 28).toFixed(1), unit: 'm', color: 'cyan' },
              { label: 'THERMAL EFFICIENCY', value: ((inj?.thermal_efficiency_indicator ?? 0.72) * 100).toFixed(1), unit: '%', color: '' },
              { label: 'CYCLE OIL', value: (cssResult?.cycle_oil ?? '—').toString(), unit: 'bbl', color: 'green' },
              { label: 'TOTAL STEAM', value: (cssResult?.cycle_steam ?? '—').toString(), unit: 't', color: 'amber' },
              { label: 'SOR', value: (cssResult?.SOR ?? '—').toString(), unit: 't/bbl', color: sorColor },
            ].map(kpi => (
              <div key={kpi.label} className="panel-card" style={{ marginBottom: 8 }}>
                <div className="telem-label">{kpi.label}</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                  <span className={`telem-value ${kpi.color}`} style={{ fontSize: 16 }}>{kpi.value}</span>
                  <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{kpi.unit}</span>
                </div>
              </div>
            ))}
          </div>

          {/* SOR gauge */}
          {cssResult && (
            <div className="panel-card">
              <div className="telem-label" style={{ marginBottom: 6 }}>SOR ASSESSMENT</div>
              <div className={`risk-badge ${cssResult.SOR > 7 ? 'high' : cssResult.SOR > 5 ? 'warning' : 'normal'}`} style={{ marginBottom: 8 }}>
                {cssResult.SOR > 7 ? 'INEFFICIENT' : cssResult.SOR > 5 ? 'MODERATE' : 'EFFICIENT'}
              </div>
              <div className="risk-bar-track">
                <div className="risk-bar-fill" style={{
                  width: `${Math.min(100, (cssResult.SOR / 10) * 100)}%`,
                  background: cssResult.SOR > 7 ? 'var(--red)' : cssResult.SOR > 5 ? 'var(--amber)' : 'var(--green)',
                }} />
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3 }}>
                Target: SOR &lt; 5 t/bbl
              </div>
            </div>
          )}

          {/* Explain block */}
          <div className="explain-block">
            <div className="explain-label">CSS PHYSICS SUMMARY</div>
            <div className="explain-text">
              Marx-Langenheim model. Steam at {params.steam_temp_c}°C reduces viscosity
              from ~5,000 cP to ~{finalVisc.toFixed(0)} cP at end of cycle.
              Heated radius: {(inj?.heated_radius_m ?? 28).toFixed(1)} m.
              Thermal efficiency: {((inj?.thermal_efficiency_indicator ?? 0.72) * 100).toFixed(1)}%.
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-ghost btn-sm" style={{ flex: 1 }} onClick={() => setScreen('twin')}>← TWIN</button>
            <button className="btn btn-primary btn-sm" style={{ flex: 1 }} onClick={() => setScreen('optimize')}>OPTIMIZE →</button>
          </div>
        </div>
      </div>
    </div>
  )
}
