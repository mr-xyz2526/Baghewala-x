import React, { useState } from 'react'
import type { OptimizationResult, AlternativePlanRow } from '../types'
import { ParetoChart } from '../charts/ParetoChart'

interface Props {
  result: OptimizationResult | null
  loading: boolean
  onRunOptimization: (ruleName: string) => void
}

const fmt = (n: number, dec = 0) => n.toLocaleString('en-IN', { maximumFractionDigits: dec })

export const OptimizationPanel: React.FC<Props> = ({
  result,
  loading,
  onRunOptimization,
}) => {
  const [selectedRule, setSelectedRule] = useState<string>('balanced_compromise')

  const handleOptimizeClick = () => {
    onRunOptimization(selectedRule)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header & Control Bar */}
      <div style={{
        background: '#fff',
        borderRadius: 10,
        padding: '16px 20px',
        border: '1px solid #dde',
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: 12,
      }}>
        <div>
          <h3 style={{ margin: 0, color: '#2c3e50', fontSize: 16 }}>
            CSS Multi-Objective Optimizer (NSGA-II + Pareto)
          </h3>
          <p style={{ margin: '4px 0 0', fontSize: 12, color: '#666' }}>
            Simultaneously optimizes Oil Output, Steam-to-Oil Ratio, and Boiler Fuel Consumption.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <label style={{ fontSize: 13, color: '#444', fontWeight: 600 }}>
            Selection Rule:
            <select
              value={selectedRule}
              onChange={e => setSelectedRule(e.target.value)}
              style={{
                marginLeft: 8,
                padding: '6px 10px',
                borderRadius: 6,
                border: '1px solid #ccc',
                fontSize: 13,
                background: '#fff',
              }}
            >
              <option value="balanced_compromise">Balanced Compromise (45% Oil / 35% SOR / 20% Steam)</option>
              <option value="max_oil_priority">Max Oil Priority (80% Oil / 15% SOR / 5% Steam)</option>
              <option value="efficiency_priority">Efficiency Priority (20% Oil / 60% SOR / 20% Steam)</option>
              <option value="steam_conservation">Steam Conservation (25% Oil / 25% SOR / 50% Steam)</option>
            </select>
          </label>

          <button
            onClick={handleOptimizeClick}
            disabled={loading}
            style={{
              padding: '8px 18px',
              background: loading ? '#95a5a6' : '#27ae60',
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              fontWeight: 700,
              fontSize: 13,
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'background 0.2s',
            }}
          >
            {loading ? 'Optimizing…' : 'Run CSS Optimizer'}
          </button>
        </div>
      </div>

      {result ? (
        <>
          {/* Objective Weighting & Non-universal plan notice banner */}
          <div style={{
            background: '#e8f4fd',
            border: '1px solid #b6e0fe',
            borderRadius: 8,
            padding: '12px 16px',
            fontSize: 12.5,
            color: '#084298',
            lineHeight: 1.5,
          }}>
            <strong>Decision Rule & Weighting Basis:</strong> {result.selection_rule_description}
          </div>

          {/* Pareto Chart Panel */}
          <div style={{ background: '#fff', borderRadius: 10, padding: 20, border: '1px solid #dde' }}>
            <ParetoChart
              allCandidates={result.all_evaluated_candidates}
              paretoCandidates={result.pareto_candidates}
              currentPlan={result.current_plan}
              selectedPlan={result.selected_plan}
            />
          </div>

          {/* Alternatives Table */}
          <div style={{ background: '#fff', borderRadius: 10, padding: 20, border: '1px solid #dde' }}>
            <h4 style={{ margin: '0 0 12px', color: '#2c3e50', fontSize: 15 }}>
              Optimization Alternatives Comparison Table
            </h4>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12.5, textAlign: 'left' }}>
                <thead>
                  <tr style={{ background: '#f8f9fa', borderBottom: '2px solid #dee2e6' }}>
                    <th style={{ padding: '8px 10px' }}>Strategy / Plan</th>
                    <th style={{ padding: '8px 10px' }}>Rate (t/d)</th>
                    <th style={{ padding: '8px 10px' }}>Press (bar)</th>
                    <th style={{ padding: '8px 10px' }}>Inj / Soak / Prod</th>
                    <th style={{ padding: '8px 10px', textAlign: 'right' }}>Cum Oil (bbl)</th>
                    <th style={{ padding: '8px 10px', textAlign: 'right' }}>SOR (t/bbl)</th>
                    <th style={{ padding: '8px 10px', textAlign: 'right' }}>Steam (t)</th>
                    <th style={{ padding: '8px 10px', textAlign: 'right' }}>Radius (m)</th>
                    <th style={{ padding: '8px 10px', textAlign: 'right' }}>Δ Oil vs Baseline</th>
                    <th style={{ padding: '8px 10px', textAlign: 'right' }}>Δ SOR vs Baseline</th>
                  </tr>
                </thead>
                <tbody>
                  {result.alternatives_table.map((row: AlternativePlanRow) => {
                    const isSelected = row.strategy.includes('Selected')
                    const isCurrent = row.strategy.includes('Current')
                    const bgColor = isSelected ? '#e6fffa' : isCurrent ? '#fff5f5' : '#fff'

                    return (
                      <tr
                        key={row.strategy}
                        style={{
                          background: bgColor,
                          borderBottom: '1px solid #eee',
                          fontWeight: isSelected || isCurrent ? 600 : 400,
                        }}
                      >
                        <td style={{ padding: '8px 10px', color: isSelected ? '#00b894' : isCurrent ? '#e74c3c' : '#333' }}>
                          {row.strategy}
                        </td>
                        <td style={{ padding: '8px 10px' }}>{row.steam_rate_tpd}</td>
                        <td style={{ padding: '8px 10px' }}>{row.steam_pressure_bar}</td>
                        <td style={{ padding: '8px 10px' }}>
                          {row.injection_days}d / {row.soak_days}d / {row.production_days}d
                        </td>
                        <td style={{ padding: '8px 10px', textAlign: 'right', color: '#27ae60' }}>
                          {fmt(row.cumulative_oil_bbl)}
                        </td>
                        <td style={{ padding: '8px 10px', textAlign: 'right', color: '#2980b9' }}>
                          {row.sor_t_per_bbl.toFixed(2)}
                        </td>
                        <td style={{ padding: '8px 10px', textAlign: 'right' }}>
                          {fmt(row.cumulative_steam_t)}
                        </td>
                        <td style={{ padding: '8px 10px', textAlign: 'right' }}>
                          {row.heated_radius_m.toFixed(1)}
                        </td>
                        <td style={{
                          padding: '8px 10px',
                          textAlign: 'right',
                          color: row.oil_delta_vs_current_bbl >= 0 ? '#27ae60' : '#e74c3c',
                        }}>
                          {row.oil_delta_vs_current_bbl > 0 ? '+' : ''}{fmt(row.oil_delta_vs_current_bbl)} bbl
                        </td>
                        <td style={{
                          padding: '8px 10px',
                          textAlign: 'right',
                          color: row.sor_delta_vs_current <= 0 ? '#27ae60' : '#e74c3c',
                        }}>
                          {row.sor_delta_vs_current > 0 ? '+' : ''}{row.sor_delta_vs_current.toFixed(2)}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Trade-Off Explanation */}
          <div style={{ background: '#fff', borderRadius: 10, padding: 20, border: '1px solid #dde' }}>
            <h4 style={{ margin: '0 0 10px', color: '#2c3e50', fontSize: 15 }}>
              Engineering Trade-Off Analysis
            </h4>
            <div style={{
              fontSize: 13,
              color: '#444',
              lineHeight: 1.6,
              whiteSpace: 'pre-line',
            }}>
              {result.explanation_of_trade_offs}
            </div>
          </div>
        </>
      ) : (
        <div style={{
          background: '#fff',
          borderRadius: 10,
          padding: 40,
          border: '1px dashed #ccc',
          textAlign: 'center',
          color: '#888',
        }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>🎯</div>
          <h4 style={{ margin: '0 0 6px', color: '#333' }}>Ready to Explore the Pareto Frontier</h4>
          <p style={{ margin: 0, fontSize: 13 }}>
            Click <strong>Run CSS Optimizer</strong> above to evaluate combinations of steam rate, injection pressure,
            and durations across cumulative oil, SOR, and steam volume.
          </p>
        </div>
      )}
    </div>
  )
}
