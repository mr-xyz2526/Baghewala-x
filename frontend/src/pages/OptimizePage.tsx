import React, { useState } from 'react'
import type { TwinRunResult, OptimizationResult, CandidatePlan } from '../types'
import type { NavScreen } from '../App'
import { api } from '../api/client'
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip,
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

const RULES = [
  { value: 'balanced_compromise', label: 'Balanced Compromise',     weights: { oil: 45, sor: 35, steam: 20 } },
  { value: 'max_oil_priority',    label: 'Max Oil Priority',         weights: { oil: 80, sor: 15, steam: 5 }  },
  { value: 'efficiency_priority', label: 'Efficiency Priority',      weights: { oil: 20, sor: 60, steam: 20 } },
  { value: 'steam_conservation',  label: 'Steam Conservation',       weights: { oil: 25, sor: 25, steam: 50 } },
]

const fmt = (n: number, dec = 0) => n.toLocaleString('en-IN', { maximumFractionDigits: dec })
const usd = (n: number) => `\$${fmt(n / 1000, 1)}k`

function DeltaTag({ value, invert = false }: { value: number; invert?: boolean }) {
  const positive = invert ? value <= 0 : value >= 0
  return (
    <span style={{
      fontFamily: 'var(--font-mono)',
      fontSize: 11,
      color: positive ? 'var(--green)' : 'var(--red)',
    }}>
      {value > 0 ? '+' : ''}{value.toFixed(1)}
    </span>
  )
}

export function OptimizePage({ twinResult, setScreen }: SharedProps) {
  const [result, setResult] = useState<OptimizationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedRule, setSelectedRule] = useState('balanced_compromise')
  const [userSelected, setUserSelected] = useState<CandidatePlan | null>(null)

  const rule = RULES.find(r => r.value === selectedRule) ?? RULES[0]
  const selected = userSelected ?? result?.selected_plan

  const runOptimizer = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.optimizer.optimize({
        current_plan: {
          steam_rate_tpd: 800,
          steam_pressure_bar: 45,
          injection_days: 18,
          soak_days: 4,
          production_days: 70,
        },
        selection_rule: {
          rule_name: selectedRule,
          weight_oil: rule.weights.oil / 100,
          weight_sor: rule.weights.sor / 100,
          weight_steam: rule.weights.steam / 100,
        },
        use_nsga2: true,
      })
      setResult(res)
      setUserSelected(null)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Optimization failed')
    } finally {
      setLoading(false)
    }
  }

  // Prepare scatter data
  const paretoIds = new Set(result?.pareto_candidates.map(c => c.plan_id) ?? [])
  const feasibles = result?.all_evaluated_candidates.filter(c => c.is_feasible) ?? []
  const otherData   = feasibles.filter(c => !paretoIds.has(c.plan_id) && c.plan_id !== result?.current_plan.plan_id && c.plan_id !== result?.selected_plan.plan_id).map(c => ({ x: +c.sor_t_per_bbl.toFixed(3), y: +c.cumulative_oil_bbl.toFixed(0), id: c.plan_id }))
  const paretoData  = feasibles.filter(c => paretoIds.has(c.plan_id) && c.plan_id !== result?.current_plan.plan_id && c.plan_id !== result?.selected_plan.plan_id).map(c => ({ x: +c.sor_t_per_bbl.toFixed(3), y: +c.cumulative_oil_bbl.toFixed(0), id: c.plan_id }))
  const currentData = result ? [{ x: +result.current_plan.sor_t_per_bbl.toFixed(3), y: +result.current_plan.cumulative_oil_bbl.toFixed(0) }] : []
  const selectedData = selected ? [{ x: +selected.sor_t_per_bbl.toFixed(3), y: +selected.cumulative_oil_bbl.toFixed(0) }] : []

  const oilDelta    = selected && result ? selected.cumulative_oil_bbl - result.current_plan.cumulative_oil_bbl : 0
  const sorDelta    = selected && result ? selected.sor_t_per_bbl    - result.current_plan.sor_t_per_bbl : 0
  const steamDelta  = selected && result ? selected.cumulative_steam_t - result.current_plan.cumulative_steam_t : 0

  const isSafe = selected?.is_feasible && (selected?.constraint_violations?.length ?? 0) === 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {/* Header */}
      <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border)', borderRadius: 8, padding: '14px 18px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h2 style={{ fontSize: 17, margin: 0, letterSpacing: '-0.01em' }}>
              PHYSICS-INFORMED MULTI-OBJECTIVE OPTIMIZATION
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: 11, margin: '4px 0 0', letterSpacing: '0.03em' }}>
              NSGA-II PARETO FRONT · CSS CYCLE OPTIMIZATION · BAGHEWALA FIELD
            </p>
          </div>

          {result && (
            <div style={{ display: 'flex', gap: 10 }}>
              {[
                { label: 'EVALUATED', value: result.constraints_summary.total_evaluated },
                { label: 'FEASIBLE', value: result.constraints_summary.feasible_candidates },
                { label: 'PARETO FRONT', value: result.pareto_candidates.length },
              ].map(pill => (
                <div key={pill.label} style={{ textAlign: 'center', padding: '6px 14px', background: 'var(--bg-card)', border: '1px solid var(--border-dim)', borderRadius: 6 }}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 16, fontWeight: 700, color: 'var(--cyan)' }}>{pill.value}</div>
                  <div className="label-xs">{pill.label}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Control bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <div className="form-group" style={{ marginBottom: 0, flex: '0 0 auto' }}>
          <label className="form-label">SELECTION RULE</label>
          <select className="form-select" value={selectedRule} onChange={e => setSelectedRule(e.target.value)}
            style={{ minWidth: 200 }}>
            {RULES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
        </div>

        <div style={{ display: 'flex', gap: 8, fontSize: 11, color: 'var(--text-muted)' }}>
          <span>Oil: <b style={{ color: 'var(--green)' }}>{rule.weights.oil}%</b></span>
          <span>SOR: <b style={{ color: 'var(--amber)' }}>{rule.weights.sor}%</b></span>
          <span>Steam: <b style={{ color: 'var(--cyan)' }}>{rule.weights.steam}%</b></span>
        </div>

        <button className="btn btn-primary btn-lg" onClick={runOptimizer} disabled={loading} style={{ marginLeft: 'auto' }}>
          {loading ? <><span className="spinner" /> OPTIMIZING…</> : '◎ RUN OPTIMIZER'}
        </button>
        {error && <div className="alert alert-danger" style={{ margin: 0, padding: '6px 12px', fontSize: 11 }}>{error}</div>}
      </div>

      {!result ? (
        /* Empty state */
        <div className="panel" style={{ textAlign: 'center', padding: 60 }}>
          <div style={{ fontSize: 36, marginBottom: 12, color: 'var(--amber)', opacity: 0.5 }}>◎</div>
          <h3 style={{ color: 'var(--text-muted)', marginBottom: 8 }}>Ready to Explore the Pareto Frontier</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, maxWidth: 400, margin: '0 auto' }}>
            Select a selection rule and click <strong style={{ color: 'var(--cyan)' }}>RUN OPTIMIZER</strong> to evaluate CSS parameter combinations
            across cumulative oil, SOR, and steam consumption objectives.
          </p>
        </div>
      ) : (
        <>
          {/* Main 3-column */}
          <div className="grid-3col">
            {/* LEFT: Current plan */}
            <div className="panel">
              <div className="panel-header">
                <div>
                  <div className="panel-title">CURRENT PLAN</div>
                  <div className="panel-subtitle">Baseline operating point</div>
                </div>
                <div className="risk-badge warning">BASELINE</div>
              </div>
              {[
                { label: 'STEAM RATE', value: result.current_plan.steam_rate_tpd.toFixed(0), unit: 't/d' },
                { label: 'STEAM PRESS.', value: result.current_plan.steam_pressure_bar.toFixed(0), unit: 'bar' },
                { label: 'INJECTION', value: result.current_plan.injection_days.toString(), unit: 'days' },
                { label: 'SOAK', value: result.current_plan.soak_days.toString(), unit: 'days' },
                { label: 'PRODUCTION', value: result.current_plan.production_days.toString(), unit: 'days' },
                { label: 'CUM. OIL', value: fmt(result.current_plan.cumulative_oil_bbl), unit: 'bbl' },
                { label: 'SOR', value: result.current_plan.sor_t_per_bbl.toFixed(2), unit: 't/bbl' },
                { label: 'TOTAL STEAM', value: fmt(result.current_plan.cumulative_steam_t), unit: 't' },
              ].map(item => (
                <div key={item.label} className="telem-item" style={{ marginBottom: 8 }}>
                  <div className="telem-label">{item.label}</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="telem-value">{item.value}</span>
                    <span style={{ fontSize: 10, color: 'var(--text-muted)', alignSelf: 'flex-end' }}>{item.unit}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* CENTER: Pareto chart */}
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">PARETO TRADE-OFF FRONTIER</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>IDEAL → HIGH OIL + LOW SOR</div>
              </div>
              <ResponsiveContainer width="100%" height={380}>
                <ScatterChart margin={{ top: 10, right: 20, bottom: 35, left: 10 }}>
                  <CartesianGrid strokeDasharray="2 4" stroke="var(--border-dim)" />
                  <XAxis type="number" dataKey="x" name="SOR"
                    tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                    label={{ value: 'Steam-to-Oil Ratio (t/bbl) — LOWER IS BETTER →', position: 'insideBottom', offset: -22, fontSize: 10, fill: 'var(--text-muted)' }}
                    domain={['auto', 'auto']} />
                  <YAxis type="number" dataKey="y" name="Cumulative Oil"
                    tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                    label={{ value: 'Cum. Oil (bbl) — HIGHER ↑', angle: -90, position: 'insideLeft', offset: -5, fontSize: 10, fill: 'var(--text-muted)' }}
                    domain={['auto', 'auto']} />
                  <Tooltip
                    contentStyle={{ background: 'var(--bg-panel)', border: '1px solid var(--border-hi)', borderRadius: 6, fontSize: 11 }}
                    cursor={{ strokeDasharray: '3 3', stroke: 'var(--border-hi)' }} />
                  <Legend verticalAlign="top" height={32} wrapperStyle={{ fontSize: 11 }} />
                  <Scatter name="Feasible Candidates" data={otherData} fill="var(--text-label)" opacity={0.4} />
                  <Scatter name="Pareto Optimal" data={paretoData} fill="var(--cyan)" opacity={0.85} />
                  <Scatter name="Current Plan" data={currentData} fill="var(--red)" />
                  <Scatter name="Selected / Recommended" data={selectedData} fill="var(--green)" />
                </ScatterChart>
              </ResponsiveContainer>
            </div>

            {/* RIGHT: Recommended setpoint */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div className="panel">
                <div className="panel-header">
                  <div>
                    <div className="panel-title">RECOMMENDED SETPOINT</div>
                    <div className="panel-subtitle">{rule.label} selection</div>
                  </div>
                </div>

                {selected && (
                  <>
                    {[
                      { label: 'STEAM RATE', current: result.current_plan.steam_rate_tpd, recommended: selected.steam_rate_tpd, unit: 't/d', color: 'amber' },
                      { label: 'INJECTION', current: result.current_plan.injection_days, recommended: selected.injection_days, unit: 'd' },
                      { label: 'SOAK', current: result.current_plan.soak_days, recommended: selected.soak_days, unit: 'd' },
                      { label: 'PRODUCTION', current: result.current_plan.production_days, recommended: selected.production_days, unit: 'd' },
                    ].map(item => (
                      <div key={item.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                        <div>
                          <div className="telem-label">{item.label}</div>
                          <div className={`telem-value ${item.color ?? ''}`} style={{ fontSize: 15 }}>
                            {item.recommended} {item.unit}
                          </div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div className="telem-label">CURRENT</div>
                          <div style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                            {item.current} {item.unit}
                          </div>
                          <DeltaTag value={item.recommended - item.current} />
                        </div>
                      </div>
                    ))}

                    <hr className="divider" />

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 10 }}>
                      <div className="panel-card">
                        <div className="telem-label">CUM OIL</div>
                        <div className="telem-value green">{fmt(selected.cumulative_oil_bbl)}</div>
                        <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>bbl</div>
                        <DeltaTag value={oilDelta} />
                      </div>
                      <div className="panel-card">
                        <div className="telem-label">SOR</div>
                        <div className={`telem-value ${sorDelta < 0 ? 'green' : 'red'}`}>{selected.sor_t_per_bbl.toFixed(2)}</div>
                        <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>t/bbl</div>
                        <DeltaTag value={sorDelta} invert={true} />
                      </div>
                    </div>

                    {/* Safety gate */}
                    <div className={`safety-gate ${isSafe ? 'safe' : 'review'}`} style={{ width: '100%', justifyContent: 'center' }}>
                      {isSafe ? '✓ SAFE TO RECOMMEND' : '⚠ REQUIRES REVIEW'}
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* WHY THIS POINT */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">WHY THIS POINT?</div>
              <div className="label-sm">EXPLAINABILITY · SYNTHETIC DEMO DATA</div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10 }}>
              {[
                {
                  label: 'WHAT?',
                  text: selected
                    ? `Steam ${selected.steam_rate_tpd}t/d, ${selected.injection_days}d injection, ${selected.soak_days}d soak, ${selected.production_days}d production.`
                    : '—',
                  color: 'var(--cyan)',
                },
                {
                  label: 'WHY?',
                  text: result.selection_rule_description ?? result.explanation_of_trade_offs?.slice(0, 180),
                  color: 'var(--amber)',
                },
                {
                  label: 'EXPECTED EFFECT?',
                  text: `Oil: ${oilDelta > 0 ? '+' : ''}${fmt(oilDelta)} bbl · SOR: ${sorDelta.toFixed(2)} · Steam: ${steamDelta > 0 ? '+' : ''}${fmt(steamDelta)} t`,
                  color: 'var(--green)',
                },
                {
                  label: 'RISK?',
                  text: selected?.constraint_violations?.length
                    ? `Constraint issues: ${selected.constraint_violations.join(', ')}`
                    : 'No constraint violations. Plan is feasible.',
                  color: isSafe ? 'var(--green)' : 'var(--orange)',
                },
                {
                  label: 'CONFIDENCE?',
                  text: selected
                    ? `Pareto rank: ${selected.pareto_rank} · Feasibility rate: ${result.constraints_summary.feasibility_rate_pct.toFixed(1)}% · NOTE: Demo validation only.`
                    : '—',
                  color: 'var(--text-muted)',
                },
              ].map(block => (
                <div key={block.label} className="explain-block" style={{ borderColor: block.color }}>
                  <div className="explain-label" style={{ color: block.color }}>{block.label}</div>
                  <div className="explain-text">{block.text}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Alternatives table */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">OPTIMIZATION ALTERNATIVES</div>
              <div className="label-sm">CLICK ROW TO SELECT CANDIDATE</div>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Strategy</th>
                    <th>Rate (t/d)</th>
                    <th>Press (bar)</th>
                    <th>Schedule (Inj/Soak/Prod)</th>
                    <th style={{ textAlign: 'right' }}>Cum Oil (bbl)</th>
                    <th style={{ textAlign: 'right' }}>SOR (t/bbl)</th>
                    <th style={{ textAlign: 'right' }}>Steam (t)</th>
                    <th style={{ textAlign: 'right' }}>Radius (m)</th>
                    <th style={{ textAlign: 'right' }}>Δ Oil</th>
                    <th style={{ textAlign: 'right' }}>Δ SOR</th>
                  </tr>
                </thead>
                <tbody>
                  {result.alternatives_table.map(row => {
                    const isSel = row.strategy.includes('Selected') || (userSelected?.plan_id === row.plan_id)
                    const isCur = row.strategy.includes('Current')
                    return (
                      <tr key={row.strategy}
                        className={isSel ? 'selected' : isCur ? 'current' : ''}
                        onClick={() => {
                          const cand = result.all_evaluated_candidates.find(c => c.plan_id === row.plan_id)
                          if (cand) setUserSelected(cand)
                        }}
                        style={{ cursor: 'pointer' }}>
                        <td style={{ color: isSel ? 'var(--cyan)' : isCur ? 'var(--red)' : 'var(--text-primary)', fontWeight: isSel || isCur ? 700 : 400 }}>
                          {row.strategy}
                        </td>
                        <td>{row.steam_rate_tpd}</td>
                        <td>{row.steam_pressure_bar}</td>
                        <td>{row.injection_days}d / {row.soak_days}d / {row.production_days}d</td>
                        <td style={{ textAlign: 'right', color: 'var(--green)' }}>{fmt(row.cumulative_oil_bbl)}</td>
                        <td style={{ textAlign: 'right', color: 'var(--cyan)' }}>{row.sor_t_per_bbl.toFixed(2)}</td>
                        <td style={{ textAlign: 'right' }}>{fmt(row.cumulative_steam_t)}</td>
                        <td style={{ textAlign: 'right' }}>{row.heated_radius_m.toFixed(1)}</td>
                        <td style={{ textAlign: 'right', color: row.oil_delta_vs_current_bbl >= 0 ? 'var(--green)' : 'var(--red)' }}>
                          {row.oil_delta_vs_current_bbl > 0 ? '+' : ''}{fmt(row.oil_delta_vs_current_bbl)}
                        </td>
                        <td style={{ textAlign: 'right', color: row.sor_delta_vs_current <= 0 ? 'var(--green)' : 'var(--red)' }}>
                          {row.sor_delta_vs_current > 0 ? '+' : ''}{row.sor_delta_vs_current.toFixed(2)}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Trade-off explanation */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">ENGINEERING TRADE-OFF ANALYSIS</div>
            </div>
            <pre style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-primary)', whiteSpace: 'pre-wrap', lineHeight: 1.7, margin: 0 }}>
              {result.explanation_of_trade_offs}
            </pre>
          </div>
        </>
      )}
    </div>
  )
}
