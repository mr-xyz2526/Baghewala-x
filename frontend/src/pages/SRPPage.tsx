import React, { useState, useCallback } from 'react'
import type { TwinRunResult, DynamometerCard, MLPredictResult, CardClass } from '../types'
import type { NavScreen } from '../App'
import { api } from '../api/client'
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

const CARD_CLASSES: { id: CardClass; label: string; color: string; badgeClass: string; desc: string }[] = [
  { id: 'NORMAL',      label: 'Normal',       color: 'var(--green)',  badgeClass: 'normal',  desc: 'Healthy pump operation — full liquid fill' },
  { id: 'FLUID_POUND', label: 'Fluid Pound',  color: 'var(--orange)', badgeClass: 'warning', desc: 'Incomplete fillage — rod impact at bottom' },
  { id: 'ROD_FLOATING',label: 'Rod Floating', color: 'var(--amber)',  badgeClass: 'warning', desc: 'Buoyancy reduces rod tension in viscous fluid' },
  { id: 'GAS_LOCK',    label: 'Gas Lock',     color: 'var(--red)',    badgeClass: 'high',    desc: 'Gas compresses in pump barrel — no discharge' },
  { id: 'TUBING_LEAK', label: 'Tubing Leak',  color: 'var(--red)',    badgeClass: 'high',    desc: 'Fluid leaks back through tubing failure' },
  { id: 'VISCOUS_DRAG',label: 'Viscous Drag', color: 'var(--amber)',  badgeClass: 'warning', desc: 'High viscosity creates excessive rod friction' },
]

// Generate representative dynamometer card shapes
function generateDemoCard(cardClass: CardClass, strokeIn: number, peakLoad: number, minLoad: number): { x: number; y: number }[] {
  const n = 80
  const pts: { x: number; y: number }[] = []
  const amp = (peakLoad - minLoad) / 2
  const mid = (peakLoad + minLoad) / 2

  for (let i = 0; i <= n; i++) {
    const t = (i / n) * 2 * Math.PI
    const x = strokeIn * 0.5 * (1 + Math.cos(t + Math.PI))

    let y = mid + amp * Math.sin(t)

    if (cardClass === 'FLUID_POUND') {
      // Fluid pound: upper stroke normal, lower stroke has sharp impact notch
      if (t > Math.PI && t < Math.PI * 1.3) {
        y = minLoad * 0.4 + amp * 0.3 * Math.sin(t * 4)
      }
    } else if (cardClass === 'ROD_FLOATING') {
      // Rod floating: min load very close to zero
      y = mid + amp * Math.sin(t) - minLoad * 0.6 * Math.sin(t / 2)
      y = Math.max(0, y)
    } else if (cardClass === 'GAS_LOCK') {
      // Gas lock: compressed parallelogram
      y = mid + amp * 0.4 * Math.sin(t)
      if (t > 0.5 && t < 1.0) y = peakLoad * 0.5
    } else if (cardClass === 'TUBING_LEAK') {
      // Tubing leak: downstroke reduced, card smaller
      y = mid * 0.75 + amp * 0.65 * Math.sin(t)
    } else if (cardClass === 'VISCOUS_DRAG') {
      // Viscous drag: card tilted, higher peak
      y = mid + amp * 1.2 * Math.sin(t) + strokeIn * 0.8 * (x / strokeIn - 0.5)
      y = Math.min(peakLoad * 1.15, Math.max(0, y))
    }

    pts.push({ x: +x.toFixed(1), y: +y.toFixed(0) })
  }
  return pts
}

function DynaCardChart({ data, title, color, height = 260 }: {
  data: { x: number; y: number }[]
  title: string
  color: string
  height?: number
}) {
  return (
    <div>
      <div className="chart-title" style={{ color }}>{title}</div>
      <div style={{ background: 'var(--bg-input)', borderRadius: 6, border: '1px solid var(--border)', padding: '4px 0' }}>
        <ResponsiveContainer width="100%" height={height}>
          <LineChart data={data} margin={{ top: 10, right: 20, bottom: 30, left: 15 }}>
            <CartesianGrid strokeDasharray="2 4" stroke="var(--border-dim)" />
            <XAxis dataKey="x"
              type="number" domain={['dataMin', 'dataMax']}
              tick={{ fill: 'var(--text-muted)', fontSize: 9, fontFamily: 'var(--font-mono)' }}
              label={{ value: 'Position (in)', position: 'insideBottom', offset: -18, fontSize: 10, fill: 'var(--text-muted)' }} />
            <YAxis
              tick={{ fill: 'var(--text-muted)', fontSize: 9, fontFamily: 'var(--font-mono)' }}
              label={{ value: 'Load (lbf)', angle: -90, position: 'insideLeft', offset: 5, fontSize: 10, fill: 'var(--text-muted)' }} />
            <Tooltip
              contentStyle={{ background: 'var(--bg-panel)', border: '1px solid var(--border-hi)', borderRadius: 6, fontSize: 10 }}
              formatter={(v: any) => [`${v} lbf`, 'Load']} />
            <Line dataKey="y" stroke={color} dot={false} strokeWidth={2} name="Load (lbf)" isAnimationActive={true} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export function SRPPage({ twinResult, setScreen }: SharedProps) {
  const srp = twinResult?.srp_point
  const risk = twinResult?.risk_score

  const [selectedClass, setSelectedClass] = useState<CardClass>('NORMAL')
  const [srpParams, setSrpParams] = useState({
    spm: srp?.spm ?? 6.0,
    stroke: srp?.stroke_length_in ?? 72,
    vfd: 36,
    fillage: srp?.pump_fillage_pct ?? 82,
    rodLength: 600,
    pumpDepth: 500,
  })
  const [dynaCard, setDynaCard] = useState<DynamometerCard | null>(null)
  const [mlResult, setMlResult] = useState<MLPredictResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Build demo card
  const peakLoad = srp?.peak_rod_load_lbf ?? 11200
  const minLoad  = srp?.min_rod_load_lbf  ?? 2800

  const currentCardData  = generateDemoCard('NORMAL', srpParams.stroke, peakLoad, minLoad)
  const simCardData      = generateDemoCard(selectedClass, srpParams.stroke, peakLoad * (selectedClass === 'NORMAL' ? 1 : selectedClass === 'FLUID_POUND' ? 0.85 : 0.9), minLoad * (selectedClass === 'ROD_FLOATING' ? 0.1 : 0.8))

  const runDynamometer = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const card = await api.srp.dynamometer({
        spm: srpParams.spm,
        surface_stroke_in: srpParams.stroke,
        pump_fillage_pct: srpParams.fillage,
        card_class: selectedClass,
        rod_length_m: srpParams.rodLength,
        prefer_numerical: true,
      })
      setDynaCard(card)

      // Then ML predict on the card
      const cardPts: [number, number][] = card.surface_card?.length > 0
        ? card.surface_card
        : currentCardData.map(p => [p.x, p.y] as [number, number])

      if (cardPts.length > 0) {
        const ml = await api.ml.predict({ card_points: cardPts })
        setMlResult(ml)
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Dynamometer computation failed')
    } finally {
      setLoading(false)
    }
  }, [srpParams, selectedClass])

  const fillageColor = srpParams.fillage < 60 ? 'var(--red)' : srpParams.fillage < 75 ? 'var(--orange)' : 'var(--green)'
  const classInfo = CARD_CLASSES.find(c => c.id === selectedClass) ?? CARD_CLASSES[0]

  const riskData = risk ?? {
    anomaly_class: 'NORMAL',
    anomaly_probability: 0.18,
    rod_floating_risk: 0.12,
    impact_risk: 0.22,
    equipment_risk: 0.15,
    flags: [],
    recommendations: ['Operating within normal parameters'],
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: 18, margin: 0 }}>SRP ANALYZER</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 12, margin: '4px 0 0' }}>
            Sucker Rod Pump · Dynamometer Analysis · Gibbs 1D Wave Solver · Synthetic Demo
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {error && <div className="alert alert-danger" style={{ margin: 0, padding: '4px 10px', fontSize: 11 }}>{error}</div>}
          <div className={`risk-badge ${riskData.anomaly_class === 'NORMAL' ? 'normal' : 'warning'}`}>{riskData.anomaly_class}</div>
          <button className="btn btn-ghost btn-sm" onClick={() => setScreen('risk')}>→ RISK CENTER</button>
        </div>
      </div>

      {/* Top KPI rail */}
      <div className="kpi-rail" style={{ gridTemplateColumns: 'repeat(8, 1fr)' }}>
        {[
          { label: 'SPM', value: srpParams.spm.toFixed(1), unit: 'str/min', color: 'cyan' },
          { label: 'STROKE', value: srpParams.stroke.toFixed(0), unit: 'in', color: '' },
          { label: 'VFD', value: srpParams.vfd.toFixed(0), unit: 'Hz', color: 'amber' },
          { label: 'FILLAGE', value: srpParams.fillage.toFixed(0), unit: '%', color: srpParams.fillage < 60 ? 'red' : srpParams.fillage < 75 ? 'orange' : 'green' },
          { label: 'PEAK LOAD', value: (srp?.peak_rod_load_lbf ?? peakLoad).toFixed(0), unit: 'lbf', color: '' },
          { label: 'MIN LOAD', value: (srp?.min_rod_load_lbf ?? minLoad).toFixed(0), unit: 'lbf', color: '' },
          { label: 'TORQUE', value: (srp?.torque_indicator_ft_lbf ?? 4800).toFixed(0), unit: 'ft·lbf', color: '' },
          { label: 'MOTOR POWER', value: (srp?.motor_power_kw ?? 28.5).toFixed(1), unit: 'kW', color: 'blue' },
        ].map(kpi => (
          <div key={kpi.label} className={`kpi-card ${kpi.color}`}>
            <div className="kpi-label">{kpi.label}</div>
            <div className="kpi-value" style={{ fontSize: 16 }}>{kpi.value}</div>
            <div className="kpi-unit">{kpi.unit}</div>
          </div>
        ))}
      </div>

      {/* Main 3-column layout */}
      <div className="grid-3col">

        {/* LEFT: Controls */}
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title">CARD CLASS & PARAMETERS</div>
          </div>

          {/* Card class selector */}
          <div style={{ marginBottom: 14 }}>
            <div className="label-sm" style={{ marginBottom: 8 }}>SELECT CARD MODE</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              {CARD_CLASSES.map(cc => (
                <button
                  key={cc.id}
                  className={`btn btn-ghost btn-sm ${selectedClass === cc.id ? 'active' : ''}`}
                  style={{
                    textAlign: 'left',
                    borderColor: selectedClass === cc.id ? cc.color : 'var(--border)',
                    color: selectedClass === cc.id ? cc.color : 'var(--text-muted)',
                    justifyContent: 'flex-start',
                  }}
                  onClick={() => setSelectedClass(cc.id)}
                >
                  {cc.label}
                </button>
              ))}
            </div>
            {selectedClass && (
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 6, lineHeight: 1.4 }}>
                {classInfo.desc}
              </div>
            )}
          </div>

          <hr className="divider" />

          {/* Parameter sliders */}
          {[
            { label: 'SPM', key: 'spm', min: 2, max: 12, step: 0.5, unit: 'str/min' },
            { label: 'Stroke Length', key: 'stroke', min: 48, max: 96, step: 6, unit: 'in' },
            { label: 'VFD Frequency', key: 'vfd', min: 20, max: 60, step: 1, unit: 'Hz' },
            { label: 'Pump Fillage', key: 'fillage', min: 20, max: 100, step: 5, unit: '%' },
          ].map(f => (
            <div key={f.key} className="form-group" style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                <label className="form-label">{f.label}</label>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600, color: 'var(--text-bright)' }}>
                  {(srpParams as any)[f.key]} {f.unit}
                </span>
              </div>
              <input type="range" className="form-slider"
                min={f.min} max={f.max} step={f.step}
                value={(srpParams as any)[f.key]}
                onChange={e => setSrpParams(p => ({ ...p, [f.key]: Number(e.target.value) }))}
              />
            </div>
          ))}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
            <div className="form-group">
              <label className="form-label">Rod Length (m)</label>
              <input type="number" className="form-input" value={srpParams.rodLength}
                onChange={e => setSrpParams(p => ({ ...p, rodLength: Number(e.target.value) }))} />
            </div>
            <div className="form-group">
              <label className="form-label">Pump Depth (m)</label>
              <input type="number" className="form-input" value={srpParams.pumpDepth}
                onChange={e => setSrpParams(p => ({ ...p, pumpDepth: Number(e.target.value) }))} />
            </div>
          </div>

          <button className="btn btn-amber btn-lg" style={{ width: '100%' }}
            onClick={runDynamometer} disabled={loading}>
            {loading ? <><span className="spinner" /> COMPUTING…</> : '⬡ RUN DYNAMOMETER'}
          </button>

          {dynaCard && (
            <div className="panel-card" style={{ marginTop: 10 }}>
              <div className="label-sm" style={{ marginBottom: 4 }}>SOLVER USED</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--cyan)' }}>
                {dynaCard.solver_used ?? 'GIBBS-1D'}
              </div>
            </div>
          )}
        </div>

        {/* CENTER: Dynacard charts */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div className="panel">
            <div className="panel-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div className="panel-title">SURFACE DYNAMOMETER CARD</div>
                <div className={`risk-badge ${classInfo.badgeClass}`} style={{ marginLeft: 8 }}>
                  {classInfo.label}
                </div>
              </div>
              <div className="label-sm">CURRENT vs SIMULATED</div>
            </div>
            <div style={{ background: 'var(--bg-input)', borderRadius: 6, border: '1px solid var(--border)', padding: '4px 0' }}>
              <ResponsiveContainer width="100%" height={280}>
                <LineChart margin={{ top: 10, right: 20, bottom: 30, left: 15 }}>
                  <CartesianGrid strokeDasharray="2 4" stroke="var(--border-dim)" />
                  <XAxis dataKey="x" type="number" domain={[0, srpParams.stroke]}
                    tick={{ fill: 'var(--text-muted)', fontSize: 9, fontFamily: 'var(--font-mono)' }}
                    label={{ value: 'Position (in)', position: 'insideBottom', offset: -18, fontSize: 10, fill: 'var(--text-muted)' }} />
                  <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 9, fontFamily: 'var(--font-mono)' }}
                    label={{ value: 'Load (lbf)', angle: -90, position: 'insideLeft', offset: 5, fontSize: 10, fill: 'var(--text-muted)' }} />
                  <Tooltip contentStyle={{ background: 'var(--bg-panel)', border: '1px solid var(--border-hi)', borderRadius: 6, fontSize: 10 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line data={currentCardData} dataKey="y" stroke="var(--cyan)" dot={false}
                    strokeWidth={2} name="Current Card" isAnimationActive={false} />
                  <Line data={simCardData} dataKey="y" stroke={classInfo.color} dot={false}
                    strokeWidth={2} name={`Simulated (${classInfo.label})`}
                    strokeDasharray={selectedClass === 'NORMAL' ? undefined : '6 2'}
                    isAnimationActive={true} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">DOWNHOLE DYNAMOMETER CARD</div>
              <div className="label-sm">COMPUTED VIA WAVE EQUATION</div>
            </div>
            <DynaCardChart
              data={dynaCard
                ? dynaCard.downhole_card.map(([x, y]) => ({ x, y }))
                : currentCardData.map(p => ({ x: p.x, y: p.y * 0.85 + peakLoad * 0.05 }))}
              title=""
              color="var(--amber)"
              height={240}
            />
          </div>

          {/* ML Prediction */}
          {mlResult && (
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">ML CLASSIFICATION RESULT</div>
                <div className="label-sm">DEMO · SYNTHETIC VALIDATION ONLY</div>
              </div>
              <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 10 }}>
                <div className={`risk-badge ${mlResult.condition === 'NORMAL' ? 'normal' : 'warning'}`} style={{ fontSize: 12 }}>
                  {mlResult.condition.replace('_', ' ')}
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--text-muted)' }}>
                  Confidence: <span style={{ color: 'var(--green)', fontWeight: 700 }}>DEMO</span>
                </div>
              </div>
              {mlResult.alternatives?.length > 0 && (
                <div>
                  <div className="label-sm" style={{ marginBottom: 4 }}>ALTERNATIVES</div>
                  {mlResult.alternatives.map((alt, i) => (
                    <div key={i} style={{ fontSize: 11, color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                      <span>{alt.condition.replace('_', ' ')}</span>
                      <span style={{ fontFamily: 'var(--font-mono)' }}>DEMO</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* RIGHT: Risk assessment */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">RISK ASSESSMENT</div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <div className={`risk-badge ${riskData.anomaly_class === 'NORMAL' ? 'normal' : riskData.anomaly_probability > 0.6 ? 'high' : 'warning'}`}>
                {riskData.anomaly_class}
              </div>
            </div>

            {[
              { label: 'Anomaly Prob.', value: riskData.anomaly_probability },
              { label: 'Rod Float', value: riskData.rod_floating_risk },
              { label: 'Impact Risk', value: riskData.impact_risk },
              { label: 'Equipment', value: riskData.equipment_risk },
            ].map(bar => {
              const pct = (bar.value * 100).toFixed(0)
              const barColor = bar.value > 0.7 ? 'var(--red)' : bar.value > 0.4 ? 'var(--orange)' : bar.value > 0.2 ? 'var(--amber)' : 'var(--green)'
              return (
                <div key={bar.label} style={{ marginBottom: 12 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em' }}>{bar.label}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700, color: barColor }}>{pct}%</span>
                  </div>
                  <div className="risk-bar-track">
                    <div className="risk-bar-fill" style={{ width: `${pct}%`, background: barColor }} />
                  </div>
                </div>
              )
            })}

            <hr className="divider" />

            {riskData.flags.length > 0 ? (
              <div>
                <div className="label-sm" style={{ marginBottom: 4 }}>FLAGS</div>
                {riskData.flags.map((f, i) => (
                  <div key={i} style={{ fontSize: 11, color: 'var(--red)', padding: '2px 0' }}>◆ {f}</div>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: 12, color: 'var(--green)' }}>✓ No active risk flags</div>
            )}

            {riskData.recommendations.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <div className="label-sm" style={{ marginBottom: 4 }}>RECOMMENDATIONS</div>
                {riskData.recommendations.map((r, i) => (
                  <div key={i} style={{ fontSize: 11, color: 'var(--text-primary)', padding: '2px 0' }}>→ {r}</div>
                ))}
              </div>
            )}
          </div>

          {/* Pump fillage indicator */}
          <div className="panel-card">
            <div className="telem-label">PUMP FILLAGE</div>
            <div className="telem-value" style={{ color: fillageColor, fontSize: 24 }}>
              {srpParams.fillage.toFixed(0)}%
            </div>
            <div className="risk-bar-track" style={{ marginTop: 6 }}>
              <div className="risk-bar-fill" style={{ width: `${srpParams.fillage}%`, background: fillageColor }} />
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3 }}>
              {srpParams.fillage < 60 ? '⚠ FLUID POUND RISK — Reduce SPM' :
               srpParams.fillage < 75 ? '⚠ LOW FILLAGE — Monitor' : '✓ NORMAL'}
            </div>
          </div>

          {/* SRP Physics Summary */}
          <div className="explain-block">
            <div className="explain-label">SRP PHYSICS SUMMARY</div>
            <div className="explain-text">
              At {srpParams.spm} SPM with {srpParams.stroke}" stroke, theoretical fluid rate is{' '}
              {(srpParams.spm * srpParams.stroke * 0.0119).toFixed(0)} bbl/d (at 100% fillage).
              Current fillage {srpParams.fillage}% → actual rate ~{(srpParams.spm * srpParams.stroke * 0.0119 * srpParams.fillage / 100).toFixed(0)} bbl/d.
              {srpParams.fillage < 65 ? ' Reduce SPM to improve fillage.' : ''}
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
