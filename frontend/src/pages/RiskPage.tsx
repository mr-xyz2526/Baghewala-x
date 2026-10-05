import React, { useState } from 'react'
import type { TwinRunResult, RiskScore, SRPPoint, RiskRequest } from '../types'
import { api } from '../api/client'
import type { NavScreen } from '../App'
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, ReferenceLine, Legend,
} from 'recharts'

interface SharedProps {
  twinResult: TwinRunResult | null
  twinLoading: boolean
  twinParams: any
  setTwinParams: (p: any) => void
  runTwin: (params?: any) => void
  setScreen: (s: NavScreen) => void
}

const RISK_SCENARIOS = [
  {
    id: 'fluid_pound',
    label: 'Fluid Pound',
    icon: '💧',
    desc: 'Incomplete pump fillage causes rod impact at bottom of stroke',
    triggers: ['Fillage < 60%', 'Min load < 1000 lbf', 'Impact visible on card'],
    mitigation: 'Reduce SPM to allow adequate fillage. Check for gas interference.',
  },
  {
    id: 'rod_floating',
    label: 'Rod Floating',
    icon: '⬆',
    desc: 'Buoyancy in viscous fluid reduces effective rod load — rod may float',
    triggers: ['High viscosity (>3000 cP)', 'Low rod weight-in-fluid', 'Min load near zero'],
    mitigation: 'Increase VFD frequency to maintain tension. Check fluid level.',
  },
  {
    id: 'impact_loading',
    label: 'Impact Loading',
    icon: '⚡',
    desc: 'Mechanical shock from abrupt direction reversal or fluid pound',
    triggers: ['Peak load > 90% allowable', 'Rod stress indicator > 0.75', 'Card shows spike'],
    mitigation: 'Reduce SPM. Check rod string taper. Inspect coupling boxes.',
  },
  {
    id: 'gas_lock',
    label: 'Gas Lock',
    icon: '🫧',
    desc: 'Gas compresses in pump barrel — no fluid discharged',
    triggers: ['GOR anomaly', 'Very low oil rate with normal stroke', 'Card distorted'],
    mitigation: 'Install gas anchor / vented traveling valve. Adjust choke.',
  },
  {
    id: 'tubing_leak',
    label: 'Tubing Leak',
    icon: '⚠',
    desc: 'Fluid returning through tubing leak reduces surface production',
    triggers: ['Oil rate drop without viscosity change', 'Power anomaly', 'Fillage OK but rate low'],
    mitigation: 'Perform pressure test. Pull and replace affected tubing joint.',
  },
  {
    id: 'viscous_drag',
    label: 'Viscous Drag',
    icon: '🛢',
    desc: 'High viscosity creates excessive friction on rod string',
    triggers: ['Viscosity > 2000 cP', 'Peak load elevated', 'Torque > limit'],
    mitigation: 'Increase steam temperature. Reduce SPM. Heat well before production.',
  },
]

const riskColor = (v: number) =>
  v > 0.7 ? 'var(--red)' : v > 0.4 ? 'var(--orange)' : v > 0.2 ? 'var(--amber)' : 'var(--green)'

const riskBgClass = (v: number) =>
  v > 0.7 ? 'high' : v > 0.4 ? 'warning' : 'normal'

// Generate safe-operating-envelope scatter data
function generateEnvelopeData() {
  const points: { visc: number; spm: number; zone: 'safe' | 'transition' | 'unsafe' }[] = []
  for (let visc = 200; visc <= 5000; visc += 200) {
    // Safe zone: lower SPM at high viscosity
    const maxSafeSpm = 12 - (visc / 5000) * 8
    const minUnsafeSpm = maxSafeSpm + 2
    points.push({ visc, spm: maxSafeSpm, zone: 'safe' })
    points.push({ visc, spm: minUnsafeSpm, zone: 'unsafe' })
    points.push({ visc, spm: maxSafeSpm + 1, zone: 'transition' })
  }
  return points
}

export function RiskPage({ twinResult, twinParams, runTwin, setScreen }: SharedProps) {
  const risk = twinResult?.risk_score
  const srp = twinResult?.srp_point
  const [customRisk, setCustomRisk] = useState<RiskScore | null>(null)
  const [loading, setLoading] = useState(false)

  // Demo values if no twin result
  const riskData: RiskScore = customRisk ?? risk ?? {
    anomaly_class: 'NORMAL',
    anomaly_probability: 0.18,
    rod_floating_risk: 0.12,
    impact_risk: 0.22,
    equipment_risk: 0.15,
    flags: [],
    recommendations: ['Operating within normal parameters', 'Monitor fillage trend'],
  }

  const srpData: SRPPoint = srp ?? {
    spm: 6.0,
    stroke_length_in: 72,
    plunger_stroke_in: 68,
    pump_fillage_pct: 82,
    theoretical_fluid_bpd: 220,
    peak_rod_load_lbf: 11200,
    min_rod_load_lbf: 2800,
    rod_stress_indicator: 0.22,
    motor_power_kw: 28.5,
    torque_indicator_ft_lbf: 4800,
    fluid_load_lbf: 5800,
    oil_rate_bopd: 187,
  }

  const envelopeData = generateEnvelopeData()
  const safeZone = envelopeData.filter(p => p.zone === 'safe')
  const transitionZone = envelopeData.filter(p => p.zone === 'transition')
  const unsafeZone = envelopeData.filter(p => p.zone === 'unsafe')

  // Current operating point on the envelope chart
  const currentVisc = twinResult?.cycle_result.full_cycle_timeline.slice(-1)[0]?.viscosity_cp ?? 850
  const currentPoint = [{ visc: currentVisc, spm: srpData.spm }]
  const recommendedPoint = [{ visc: currentVisc, spm: Math.max(2, srpData.spm - 1.5) }]

  const overallRisk = riskData.anomaly_probability
  const overallClass = overallRisk > 0.7 ? 'critical' : overallRisk > 0.4 ? 'high' : overallRisk > 0.2 ? 'warning' : 'normal'

  const runCustomRisk = async () => {
    setLoading(true)
    try {
      const result = await api.risk.score({
        pump_fillage_pct: srpData.pump_fillage_pct,
        peak_rod_load_lbf: srpData.peak_rod_load_lbf,
        min_rod_load_lbf: srpData.min_rod_load_lbf,
        rod_stress_indicator: srpData.rod_stress_indicator,
        motor_power_kw: srpData.motor_power_kw,
        oil_rate_bopd: srpData.oil_rate_bopd,
      })
      setCustomRisk(result)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const riskBars = [
    { label: 'Overall Anomaly', value: riskData.anomaly_probability, key: 'anomaly' },
    { label: 'Rod Float Risk', value: riskData.rod_floating_risk, key: 'float' },
    { label: 'Impact / Overload', value: riskData.impact_risk, key: 'impact' },
    { label: 'Equipment Risk', value: riskData.equipment_risk, key: 'equip' },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h2 style={{ fontSize: 18, margin: 0 }}>SAFETY & RISK CENTER</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 12, margin: '4px 0 0' }}>
            SRP anomaly classification · Operating envelope · Failure mode detection
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <div className={`risk-badge ${overallClass}`} style={{ fontSize: 13, padding: '6px 16px' }}>
            {riskData.anomaly_class}
          </div>
          <button className="btn btn-ghost btn-sm" onClick={runCustomRisk} disabled={loading}>
            {loading ? <><span className="spinner" /> SCORING…</> : '↻ SCORE RISK'}
          </button>
          <button className="btn btn-primary btn-sm" onClick={() => { runTwin(); setScreen('srp') }}>
            → SRP ANALYZER
          </button>
        </div>
      </div>

      {/* Main grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>

        {/* LEFT: Risk Score Panel */}
        <div className="panel">
          <div className="panel-header">
            <div>
              <div className="panel-title">ANOMALY RISK SCORES</div>
              <div className="panel-subtitle">Physics-rule-based scoring · Demo data</div>
            </div>
            <div className={`risk-badge ${overallClass}`}>
              {(riskData.anomaly_probability * 100).toFixed(0)}% ANOMALY
            </div>
          </div>

          {riskBars.map(bar => (
            <div key={bar.key} style={{ marginBottom: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                <span style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em' }}>{bar.label}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 700, color: riskColor(bar.value) }}>
                  {(bar.value * 100).toFixed(0)}%
                </span>
              </div>
              <div className="risk-bar-track">
                <div
                  className="risk-bar-fill"
                  style={{ width: `${(bar.value * 100).toFixed(0)}%`, background: riskColor(bar.value) }}
                />
              </div>
            </div>
          ))}

          <hr className="divider" />

          {/* Flags */}
          {riskData.flags.length > 0 ? (
            <div style={{ marginBottom: 12 }}>
              <div className="label-sm" style={{ marginBottom: 6 }}>ACTIVE FLAGS</div>
              {riskData.flags.map((f, i) => (
                <div key={i} style={{ fontSize: 12, color: 'var(--red)', padding: '3px 0', display: 'flex', gap: 6 }}>
                  <span>◆</span><span>{f}</span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ fontSize: 12, color: 'var(--green)', marginBottom: 12 }}>✓ No active risk flags</div>
          )}

          {/* Recommendations */}
          <div className="label-sm" style={{ marginBottom: 6 }}>RECOMMENDATIONS</div>
          {riskData.recommendations.map((r, i) => (
            <div key={i} style={{ fontSize: 12, color: 'var(--text-primary)', padding: '3px 0', display: 'flex', gap: 6 }}>
              <span style={{ color: 'var(--green)' }}>→</span><span>{r}</span>
            </div>
          ))}
        </div>

        {/* RIGHT: Safe Operating Envelope */}
        <div className="panel">
          <div className="panel-header">
            <div>
              <div className="panel-title">SAFE OPERATING ENVELOPE</div>
              <div className="panel-subtitle">SPM vs. Oil Viscosity · Modeled constraint boundary</div>
            </div>
          </div>

          <div className="chart-title">SPM (strokes/min) vs. Oil Viscosity (cP)</div>
          <ResponsiveContainer width="100%" height={280}>
            <ScatterChart margin={{ top: 10, right: 20, bottom: 30, left: 10 }}>
              <CartesianGrid strokeDasharray="2 4" stroke="var(--border-dim)" />
              <XAxis
                type="number" dataKey="visc" name="Viscosity" unit=" cP"
                label={{ value: 'Oil Viscosity (cP) →', position: 'insideBottom', offset: -18, fontSize: 11, fill: 'var(--text-muted)' }}
                domain={[0, 5200]} tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
              />
              <YAxis
                type="number" dataKey="spm" name="SPM" unit=" spm"
                label={{ value: 'SPM →', angle: -90, position: 'insideLeft', offset: 10, fontSize: 11, fill: 'var(--text-muted)' }}
                domain={[0, 14]} tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
              />
              <Tooltip
                contentStyle={{ background: 'var(--bg-panel)', border: '1px solid var(--border-hi)', borderRadius: 6, fontSize: 11 }}
                labelStyle={{ color: 'var(--text-primary)' }}
                cursor={{ strokeDasharray: '3 3', stroke: 'var(--border-hi)' }}
              />
              <Legend verticalAlign="top" height={28} wrapperStyle={{ fontSize: 11 }} />
              <Scatter name="Safe Zone" data={safeZone} fill="var(--green)" opacity={0.25} r={3} />
              <Scatter name="Transition" data={transitionZone} fill="var(--amber)" opacity={0.35} r={3} />
              <Scatter name="Unsafe Zone" data={unsafeZone} fill="var(--red)" opacity={0.25} r={3} />
              <Scatter name="Current Operating Point" data={currentPoint} fill="var(--red)" opacity={1} r={7} />
              <Scatter name="Recommended Point" data={recommendedPoint} fill="var(--green)" opacity={1} r={7} />
            </ScatterChart>
          </ResponsiveContainer>

          <div style={{ display: 'flex', gap: 12, marginTop: 8, fontSize: 11 }}>
            <span style={{ color: 'var(--green)' }}>● Safe Zone</span>
            <span style={{ color: 'var(--amber)' }}>● Transition</span>
            <span style={{ color: 'var(--red)' }}>● Unsafe</span>
            <span style={{ color: 'var(--red)', fontWeight: 700 }}>▲ Current ({currentVisc.toFixed(0)} cP, {srpData.spm.toFixed(1)} spm)</span>
            <span style={{ color: 'var(--green)', fontWeight: 700 }}>★ Recommended</span>
          </div>
        </div>
      </div>

      {/* Failure Mode Cards Grid */}
      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">FAILURE MODE LIBRARY</div>
          <div className="panel-subtitle">Common SRP anomalies · Status based on current operating point</div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
          {RISK_SCENARIOS.map(scenario => {
            const riskVal =
              scenario.id === 'fluid_pound' ? (srpData.pump_fillage_pct < 60 ? 0.8 : riskData.anomaly_probability * 0.6) :
              scenario.id === 'rod_floating' ? riskData.rod_floating_risk :
              scenario.id === 'impact_loading' ? riskData.impact_risk :
              riskData.equipment_risk * 0.5 + Math.random() * 0.1

            const cls = riskBgClass(riskVal)
            const borderColor = riskVal > 0.7 ? 'var(--red)' : riskVal > 0.4 ? 'var(--orange)' : riskVal > 0.2 ? 'var(--amber)' : 'var(--border-dim)'

            return (
              <div key={scenario.id} className="panel-card" style={{ borderLeft: `3px solid ${borderColor}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-bright)', display: 'flex', gap: 6, alignItems: 'center' }}>
                    <span>{scenario.icon}</span>
                    <span>{scenario.label}</span>
                  </div>
                  <div className={`risk-badge ${cls}`} style={{ fontSize: 9 }}>
                    {(riskVal * 100).toFixed(0)}%
                  </div>
                </div>

                <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: '0 0 8px', lineHeight: 1.5 }}>
                  {scenario.desc}
                </p>

                <div style={{ marginBottom: 6 }}>
                  <div className="label-xs" style={{ marginBottom: 3 }}>TRIGGERS</div>
                  {scenario.triggers.map((t, i) => (
                    <div key={i} style={{ fontSize: 10, color: 'var(--text-muted)', lineHeight: 1.5 }}>• {t}</div>
                  ))}
                </div>

                <div>
                  <div className="label-xs" style={{ marginBottom: 3, color: 'var(--green)' }}>MITIGATION</div>
                  <div style={{ fontSize: 10, color: 'var(--green)', lineHeight: 1.5 }}>{scenario.mitigation}</div>
                </div>

                {/* Mini risk bar */}
                <div className="risk-bar-track" style={{ marginTop: 8 }}>
                  <div className="risk-bar-fill" style={{ width: `${(riskVal * 100).toFixed(0)}%`, background: borderColor }} />
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Explainability */}
      <div className="explain-block">
        <div className="explain-label">RISK ANALYSIS METHODOLOGY</div>
        <div className="explain-text">
          Risk scores are computed from rule-based physics indicators: pump fillage (fluid pound risk),
          rod weight-in-fluid vs. buoyancy (rod float), load amplification factor (impact loading),
          and motor power anomaly (equipment risk). Scores range 0–1. Thresholds are model-defined,
          not calibrated to field history. All values are synthetic-demo only.
        </div>
      </div>
    </div>
  )
}
