import React, { useState } from 'react'
import type { TwinRunResult } from '../types'
import type { NavScreen } from '../App'
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

// Animated Well Cross-Section SVG
function WellCrossSection({ phase, tempC, heatedRadius }: { phase: string; tempC: number; heatedRadius: number }) {
  const isInjecting = phase === 'INJECTION'
  const isSoaking   = phase === 'SOAKING'

  // Normalize heated radius to SVG scale (0-80 pixels from center)
  const heatPx = Math.min(80, Math.max(20, heatedRadius * 2.5))

  return (
    <svg width="100%" viewBox="0 0 240 480" xmlns="http://www.w3.org/2000/svg"
      style={{ background: 'var(--bg-input)', borderRadius: 6, border: '1px solid var(--border)' }}>

      {/* Background strata */}
      <rect x="0" y="0" width="240" height="480" fill="#080c18" />
      {/* Surface layer */}
      <rect x="0" y="0" width="240" height="30" fill="#12193a" />
      <text x="10" y="20" fontSize="9" fill="#4a6480" fontFamily="var(--font-mono)">SURFACE  0 m</text>

      {/* Formation layers */}
      {[
        { y: 100, label: '100 m', color: '#0e1628' },
        { y: 200, label: '200 m', color: '#111929' },
        { y: 300, label: '300 m', color: '#0e1628' },
        { y: 380, label: '380 m', color: '#141c35' },
        { y: 440, label: '500 m (RESERVOIR)', color: '#101520' },
      ].map(layer => (
        <g key={layer.y}>
          <line x1="0" y1={layer.y} x2="240" y2={layer.y} stroke="#1a2840" strokeWidth="0.5" strokeDasharray="4 4" />
          <text x="8" y={layer.y + 11} fontSize="8" fill="#2d4060" fontFamily="var(--font-mono)">{layer.label}</text>
        </g>
      ))}

      {/* Heated zone (radial thermal plume around reservoir) */}
      {(isInjecting || isSoaking || tempC > 120) && (
        <>
          {/* Outer glow */}
          <ellipse cx="120" cy="420" rx={heatPx * 1.4} ry={heatPx * 0.5}
            fill="rgba(245,158,11,0.06)" />
          <ellipse cx="120" cy="420" rx={heatPx * 1.1} ry={heatPx * 0.4}
            fill="rgba(245,158,11,0.12)" />
          <ellipse cx="120" cy="420" rx={heatPx * 0.75} ry={heatPx * 0.28}
            fill="rgba(249,115,22,0.18)" />
          <ellipse cx="120" cy="420" rx={heatPx * 0.45} ry={heatPx * 0.17}
            fill="rgba(239,68,68,0.22)" />
        </>
      )}

      {/* Casing (outer, cement) */}
      <rect x="106" y="30" width="4" height="440" fill="#243650" />
      <rect x="130" y="30" width="4" height="440" fill="#243650" />

      {/* Tubing string */}
      <rect x="113" y="30" width="2" height="420" fill="#3b82f6" opacity="0.7" />
      <rect x="125" y="30" width="2" height="420" fill="#3b82f6" opacity="0.7" />

      {/* Rod string (animated) */}
      <g className={isInjecting ? '' : 'pump-rod-animated'}>
        <rect x="118.5" y="10" width="3" height="400" fill="#f59e0b" opacity="0.8" />
      </g>

      {/* Pump (downhole) */}
      <rect x="112" y="400" width="16" height="24" rx="2" fill="#1e3a8a" stroke="#3b82f6" strokeWidth="0.5" />
      <text x="120" y="415" textAnchor="middle" fontSize="7" fill="#60a5fa" fontFamily="var(--font-mono)">PUMP</text>

      {/* Perforations at reservoir */}
      {[415, 425, 435, 445].map(py => (
        <g key={py}>
          <line x1="106" y1={py} x2="90" y2={py} stroke="#f59e0b" strokeWidth="0.8" opacity="0.5" />
          <line x1="134" y1={py} x2="150" y2={py} stroke="#f59e0b" strokeWidth="0.8" opacity="0.5" />
        </g>
      ))}

      {/* Steam injection arrows (animated when injecting) */}
      {isInjecting && (
        <>
          {[0, 1, 2].map(i => (
            <g key={i} style={{ animation: `steam-rise ${1.5 + i * 0.5}s ease-out ${i * 0.4}s infinite` }}>
              <ellipse cx={100 + i * 12} cy={380 - i * 15} rx="4" ry="2" fill="rgba(245,158,11,0.4)" />
            </g>
          ))}
        </>
      )}

      {/* Polished rod / surface */}
      <rect x="117" y="0" width="6" height="30" fill="#f59e0b" />
      <rect x="105" y="25" width="30" height="8" rx="2" fill="#1e3a8a" stroke="#3b82f6" strokeWidth="0.5" />

      {/* Pump jack icon at surface */}
      <text x="120" y="15" textAnchor="middle" fontSize="10" fill="#f59e0b">⬡</text>

      {/* Temperature annotation */}
      <rect x="148" y="405" width="68" height="22" rx="3" fill="rgba(245,158,11,0.1)" stroke="rgba(245,158,11,0.3)" strokeWidth="0.5" />
      <text x="152" y="414" fontSize="7" fill="#f59e0b" fontFamily="var(--font-mono)">TEMP</text>
      <text x="152" y="424" fontSize="9" fill="#f59e0b" fontWeight="bold" fontFamily="var(--font-mono)">{tempC.toFixed(0)} °C</text>

      {/* Phase label */}
      <rect x="8" y="395" width="68" height="22" rx="3"
        fill={isInjecting ? 'rgba(245,158,11,0.12)' : isSoaking ? 'rgba(139,92,246,0.12)' : 'rgba(16,185,129,0.1)'}
        stroke={isInjecting ? 'rgba(245,158,11,0.4)' : isSoaking ? 'rgba(139,92,246,0.4)' : 'rgba(16,185,129,0.3)'}
        strokeWidth="0.5" />
      <text x="12" y="404" fontSize="7"
        fill={isInjecting ? '#f59e0b' : isSoaking ? '#a78bfa' : '#10b981'}
        fontFamily="var(--font-mono)">PHASE</text>
      <text x="12" y="415" fontSize="8"
        fill={isInjecting ? '#f59e0b' : isSoaking ? '#a78bfa' : '#10b981'}
        fontWeight="bold" fontFamily="var(--font-mono)">
        {isInjecting ? 'INJECTION' : isSoaking ? 'SOAK' : 'PRODUCTION'}
      </text>

      {/* Depth scale */}
      <line x1="6" y1="30" x2="6" y2="460" stroke="#1a2840" strokeWidth="1" />
      {[0, 100, 200, 300, 400, 500].map((d, i) => (
        <line key={d} x1="4" y1={30 + i * 86} x2="8" y2={30 + i * 86} stroke="#3d5470" strokeWidth="1" />
      ))}
    </svg>
  )
}

export function WellTwinPage({ twinResult, twinLoading, twinParams, setTwinParams, runTwin, setScreen }: SharedProps) {
  const timeline = twinResult?.cycle_result.full_cycle_timeline ?? []
  const lastRecord = timeline.slice(-1)[0]
  const phase = lastRecord?.phase ?? 'PRODUCTION'
  const tempC = lastRecord?.temperature_c ?? 184
  const viscCp = lastRecord?.viscosity_cp ?? 420
  const oilRate = lastRecord?.oil_rate_bopd ?? 187
  const pb = twinResult?.cycle_result.phase_boundaries
  const injection = twinResult?.cycle_result.injection_summary
  const srp = twinResult?.srp_point
  const risk = twinResult?.risk_score

  const heatedRadius = injection?.heated_radius_m ?? 28

  const chartData = timeline.map(r => ({
    day: r.day,
    temp: +r.temperature_c.toFixed(1),
    visc: +r.viscosity_cp.toFixed(0),
    oil:  +r.oil_rate_bopd.toFixed(1),
    steam: +r.steam_rate_tpd.toFixed(0),
    cumOil: +r.cumulative_oil_bbl.toFixed(0),
  }))

  // Demo chart data if no result
  const demoData = (() => {
    if (chartData.length > 0) return chartData
    const d = []
    for (let day = 0; day <= 92; day++) {
      const inj = day < 18
      const soak = day >= 18 && day < 22
      const decay = Math.exp(-(day - 22) * 0.022)
      d.push({
        day,
        temp: inj ? 260 : soak ? 240 : +(190 * decay + 100).toFixed(1),
        visc: inj ? 120 : soak ? 180 : +(350 + (1 - decay) * 800).toFixed(0),
        oil:  inj || soak ? 0 : +(210 * decay + 65).toFixed(1),
        steam: inj ? 800 : 0,
        cumOil: day > 22 ? day * 50 : 0,
      })
    }
    return d
  })()

  const anomalyClass = risk?.anomaly_class ?? 'NORMAL'
  const anomalyProb  = risk?.anomaly_probability ?? 0.18
  const riskBadgeClass = anomalyClass === 'NORMAL' ? 'normal' : anomalyProb > 0.6 ? 'high' : 'warning'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: 18, margin: 0 }}>WELL DIGITAL TWIN — BW-101</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 12, margin: '4px 0 0' }}>
            Baghewala Field · CSS + SRP Integrated Model · Synthetic Demo
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <div className={`phase-badge ${phase.toLowerCase()}`}>
            {phase === 'INJECTION' ? '♨' : phase === 'SOAKING' ? '◎' : '↑'} {phase}
          </div>
          <div className={`risk-badge ${riskBadgeClass}`}>{anomalyClass}</div>
          <button
            className="btn btn-primary"
            onClick={() => runTwin()}
            disabled={twinLoading}
          >
            {twinLoading ? <><span className="spinner" /> RUNNING…</> : '▶ RUN TWIN'}
          </button>
        </div>
      </div>

      {/* Top KPI Rail */}
      <div className="kpi-rail" style={{ gridTemplateColumns: 'repeat(7, 1fr)' }}>
        {[
          { label: 'RESERVOIR TEMP', value: tempC.toFixed(1),   unit: '°C',   color: 'amber' },
          { label: 'VISCOSITY',      value: viscCp.toFixed(0),  unit: 'cP',   color: 'cyan' },
          { label: 'OIL RATE',       value: oilRate.toFixed(0), unit: 'BOPD', color: 'green' },
          { label: 'SPM',            value: (srp?.spm ?? 6.0).toFixed(1),  unit: 'spm', color: '' },
          { label: 'VFD',            value: (twinParams.vfd_hz ?? 36).toFixed(0), unit: 'Hz', color: 'amber' },
          { label: 'FILLAGE',        value: (srp?.pump_fillage_pct ?? 82).toFixed(0), unit: '%', color: (srp?.pump_fillage_pct ?? 82) < 65 ? 'red' : 'green' },
          { label: 'SOR',            value: (twinResult?.cycle_result.SOR ?? 4.3).toFixed(2), unit: 't/bbl', color: '' },
        ].map(kpi => (
          <div key={kpi.label} className={`kpi-card ${kpi.color}`}>
            <div className="kpi-label">{kpi.label}</div>
            <div className="kpi-value">{kpi.value}</div>
            <div className="kpi-unit">{kpi.unit}</div>
          </div>
        ))}
      </div>

      {/* Main content: cross-section + charts */}
      <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr 240px', gap: 14, alignItems: 'start' }}>

        {/* Well cross-section */}
        <div>
          <div className="label-sm" style={{ marginBottom: 6, textAlign: 'center' }}>WELL CROSS-SECTION</div>
          <WellCrossSection phase={phase} tempC={tempC} heatedRadius={heatedRadius} />
          {/* Depth annotations */}
          <div style={{ fontSize: 9, color: 'var(--text-label)', marginTop: 6, textAlign: 'center', fontFamily: 'var(--font-mono)' }}>
            Total depth ~500 m · Pump at 380 m
          </div>
          {/* Heated radius callout */}
          {injection && (
            <div className="panel-card" style={{ marginTop: 8, textAlign: 'center' }}>
              <div className="telem-label">HEATED RADIUS</div>
              <div className="telem-value amber">{heatedRadius.toFixed(1)} m</div>
              <div style={{ fontSize: 9, color: 'var(--text-muted)' }}>
                Area: {injection.heated_area_m2.toFixed(0)} m²
              </div>
            </div>
          )}
        </div>

        {/* Charts */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* Temperature + Viscosity */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">RESERVOIR TEMPERATURE & OIL VISCOSITY</div>
            </div>
            {/* CSS cycle timeline */}
            {pb && (
              <div className="cycle-timeline" style={{ marginBottom: 10 }}>
                <div className="cycle-phase injection" style={{ flex: pb.injection.end_day - pb.injection.start_day }}>
                  INJ {pb.injection.end_day - pb.injection.start_day}d
                </div>
                <div className="cycle-phase soak" style={{ flex: pb.soak.end_day - pb.soak.start_day }}>
                  SOAK {pb.soak.end_day - pb.soak.start_day}d
                </div>
                <div className="cycle-phase production" style={{ flex: Math.min(pb.production.end_day - pb.production.start_day, 80) }}>
                  PROD {pb.production.end_day - pb.production.start_day}d
                </div>
              </div>
            )}
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={demoData} margin={{ top: 5, right: 25, bottom: 5, left: 10 }}>
                <CartesianGrid strokeDasharray="2 4" stroke="var(--border-dim)" />
                <XAxis dataKey="day"
                  tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                  label={{ value: 'Day', position: 'insideBottomRight', offset: -5, fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis yAxisId="l" stroke="var(--amber)"
                  tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                  label={{ value: 'Temp (°C)', angle: -90, position: 'insideLeft', fontSize: 10, fill: 'var(--amber)' }} />
                <YAxis yAxisId="r" orientation="right" stroke="var(--cyan)" scale="log" domain={['auto', 'auto']}
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

          {/* Oil Rate + Steam */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">OIL RATE & STEAM INJECTION</div>
            </div>
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={demoData} margin={{ top: 5, right: 25, bottom: 5, left: 10 }}>
                <CartesianGrid strokeDasharray="2 4" stroke="var(--border-dim)" />
                <XAxis dataKey="day"
                  tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                  label={{ value: 'Day', position: 'insideBottomRight', offset: -5, fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis yAxisId="l" stroke="var(--green)"
                  tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                  label={{ value: 'Oil (BOPD)', angle: -90, position: 'insideLeft', fontSize: 10, fill: 'var(--green)' }} />
                <YAxis yAxisId="r" orientation="right" stroke="var(--amber)"
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

        {/* RIGHT: Downhole telemetry callouts */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">DOWNHOLE STATE</div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {[
                { label: 'Reservoir Pressure', value: '42.5', unit: 'bar', color: '' },
                { label: 'Pump Intake Pressure', value: '22.8', unit: 'bar', color: '' },
                { label: 'Wellhead Pressure', value: '5.2', unit: 'bar', color: '' },
                { label: 'Peak Rod Load', value: (srp?.peak_rod_load_lbf ?? 11200).toFixed(0), unit: 'lbf', color: '' },
                { label: 'Min Rod Load', value: (srp?.min_rod_load_lbf ?? 2800).toFixed(0), unit: 'lbf', color: '' },
                { label: 'Fluid Load', value: (srp?.fluid_load_lbf ?? 5800).toFixed(0), unit: 'lbf', color: '' },
                { label: 'Torque', value: (srp?.torque_indicator_ft_lbf ?? 4800).toFixed(0), unit: 'ft·lbf', color: '' },
                { label: 'Motor Power', value: (srp?.motor_power_kw ?? 28.5).toFixed(1), unit: 'kW', color: '' },
              ].map(item => (
                <div key={item.label} className="telem-item">
                  <div className="telem-label">{item.label}</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className={`telem-value ${item.color}`}>{item.value}</span>
                    <span style={{ fontSize: 10, color: 'var(--text-muted)', alignSelf: 'flex-end' }}>{item.unit}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-ghost btn-sm" style={{ flex: 1 }} onClick={() => setScreen('srp')}>→ SRP</button>
            <button className="btn btn-ghost btn-sm" style={{ flex: 1 }} onClick={() => setScreen('optimize')}>→ OPTIMIZE</button>
          </div>

          {/* Explainability */}
          <div className="explain-block">
            <div className="explain-label">TWIN STATE</div>
            <div className="explain-text">
              {phase === 'INJECTION'
                ? `Steam at ${tempC.toFixed(0)}°C drives thermal front into reservoir. Heated radius: ${heatedRadius.toFixed(1)} m.`
                : phase === 'SOAKING'
                ? `Thermal soak. Heat conducting radially. Viscosity reducing toward ${viscCp.toFixed(0)} cP.`
                : `Production phase. Viscosity ${viscCp.toFixed(0)} cP at ${tempC.toFixed(0)}°C. Oil rate ${oilRate.toFixed(0)} BOPD.`}
            </div>
          </div>
        </div>
      </div>

      {/* Economics strip */}
      {twinResult && (
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title">CYCLE ECONOMICS</div>
          </div>
          <div className="kpi-rail" style={{ gridTemplateColumns: 'repeat(6, 1fr)' }}>
            {[
              { label: 'CYCLE OIL', value: twinResult.cycle_result.cycle_oil.toFixed(0), unit: 'bbl', color: 'green' },
              { label: 'TOTAL STEAM', value: twinResult.cycle_result.cycle_steam.toFixed(0), unit: 't', color: 'amber' },
              { label: 'SOR', value: twinResult.cycle_result.SOR.toFixed(2), unit: 't/bbl', color: '' },
              { label: 'GROSS REVENUE', value: `$${(twinResult.economics.gross_revenue_usd / 1000).toFixed(0)}k`, unit: 'USD', color: 'green' },
              { label: 'NET CASH FLOW', value: `$${(twinResult.economics.net_cash_flow_usd / 1000).toFixed(0)}k`, unit: 'USD', color: twinResult.economics.net_cash_flow_usd >= 0 ? 'green' : 'red' },
              { label: 'ECONOMIC?', value: twinResult.economics.is_economic ? 'YES' : 'NO', unit: '', color: twinResult.economics.is_economic ? 'green' : 'red' },
            ].map(kpi => (
              <div key={kpi.label} className={`kpi-card ${kpi.color}`}>
                <div className="kpi-label">{kpi.label}</div>
                <div className="kpi-value">{kpi.value}</div>
                {kpi.unit && <div className="kpi-unit">{kpi.unit}</div>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
