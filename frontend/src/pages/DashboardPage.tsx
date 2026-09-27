import React, { useState, useCallback } from 'react'
import { api } from '../api/client'
import { ControlPanel } from '../components/ControlPanel'
import { EconomicsDashboard } from '../components/EconomicsDashboard'
import { RiskPanel } from '../components/RiskPanel'
import { CycleChart } from '../charts/CycleChart'
import { OptimizationPanel } from '../components/OptimizationPanel'
import type { TwinRunRequest, TwinRunResult, OptimizationResult } from '../types'

const DEFAULTS: TwinRunRequest = {
  well_id: 'demo-well-001',
  well_name: 'Baghewala Demo Well',
  field_name: 'Demo Field',
  steam_rate_tpd: 800,
  steam_temp_c: 260,
  injection_days: 18,
  steam_quality: 0.8,
  soak_days: 4,
  production_days: 70,
  spm: 6,
  vfd_hz: 36,
  water_cut_pct: 30,
  oil_price_usd_bbl: 60,
  steam_cost_usd_tonne: 12,
}

export const DashboardPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'simulation' | 'optimization'>('simulation')
  const [result, setResult] = useState<TwinRunResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Optimization state
  const [optResult, setOptResult] = useState<OptimizationResult | null>(null)
  const [optLoading, setOptLoading] = useState(false)

  const handleRun = useCallback(async (params: TwinRunRequest) => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.twin.run(params)
      setResult(res)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string }
      setError(e?.response?.data?.detail ?? e?.message ?? 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [])

  const handleRunOptimization = useCallback(async (ruleName: string) => {
    setOptLoading(true)
    setError(null)
    try {
      let weightOil = 0.45
      let weightSor = 0.35
      let weightSteam = 0.20

      if (ruleName === 'max_oil_priority') {
        weightOil = 0.80
        weightSor = 0.15
        weightSteam = 0.05
      } else if (ruleName === 'efficiency_priority') {
        weightOil = 0.20
        weightSor = 0.60
        weightSteam = 0.20
      } else if (ruleName === 'steam_conservation') {
        weightOil = 0.25
        weightSor = 0.25
        weightSteam = 0.50
      }

      const res = await api.optimizer.optimize({
        current_plan: {
          steam_rate_tpd: 800,
          steam_pressure_bar: 45,
          injection_days: 18,
          soak_days: 4,
          production_days: 70,
        },
        selection_rule: {
          rule_name: ruleName,
          weight_oil: weightOil,
          weight_sor: weightSor,
          weight_steam: weightSteam,
        },
        use_nsga2: true,
      })
      setOptResult(res)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string }
      setError(e?.response?.data?.detail ?? e?.message ?? 'Optimization failed')
    } finally {
      setOptLoading(false)
    }
  }, [])

  return (
    <div style={{ maxWidth: 1320, margin: '0 auto', padding: '16px 20px', fontFamily: 'system-ui, sans-serif' }}>
      {/* Header */}
      <div style={{
        background: 'linear-gradient(135deg, #1a2980, #26d0ce)',
        borderRadius: 12, padding: '18px 24px', marginBottom: 16, color: '#fff',
      }}>
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800 }}>BAGHEWALA-X Digital Twin & Optimizer</h1>
        <p style={{ margin: '4px 0 0', fontSize: 13, opacity: 0.85 }}>
          PS SIH26120 · Cyclic Steam Stimulation Analytical Simulator & Pareto Optimization · Synthetic Data Only
        </p>
      </div>

      {/* Prototype Notice Banner */}
      <div style={{
        background: '#fff8e1', border: '1px solid #ffe082', borderRadius: 8,
        padding: '8px 14px', marginBottom: 16, fontSize: 12, color: '#7a5c00',
      }}>
        <strong>Prototype Notice:</strong> All results use <em>synthetic parameters</em>.
        No field calibration claimed. Model documentation: <code>docs/MODEL_CARD.md</code> and <code>docs/ASSUMPTIONS.md</code>.
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 18 }}>
        <button
          onClick={() => setActiveTab('simulation')}
          style={{
            padding: '10px 20px',
            borderRadius: 8,
            border: 'none',
            fontWeight: 700,
            fontSize: 13.5,
            cursor: 'pointer',
            background: activeTab === 'simulation' ? '#1a2980' : '#e2e8f0',
            color: activeTab === 'simulation' ? '#fff' : '#4a5568',
            transition: 'all 0.2s',
          }}
        >
          📈 Digital Twin Simulation & Monitoring
        </button>

        <button
          onClick={() => setActiveTab('optimization')}
          style={{
            padding: '10px 20px',
            borderRadius: 8,
            border: 'none',
            fontWeight: 700,
            fontSize: 13.5,
            cursor: 'pointer',
            background: activeTab === 'optimization' ? '#1a2980' : '#e2e8f0',
            color: activeTab === 'optimization' ? '#fff' : '#4a5568',
            transition: 'all 0.2s',
          }}
        >
          🎯 Pareto Multi-Objective Optimizer
        </button>
      </div>

      {/* Global Error Banner */}
      {error && (
        <div style={{ background: '#fdecea', border: '1px solid #f5c6cb', borderRadius: 8, padding: 12, color: '#842029', marginBottom: 16 }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Tab 1: Simulation View */}
      {activeTab === 'simulation' && (
        <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 20, alignItems: 'start' }}>
          {/* Left: Controls + Risk */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <ControlPanel defaults={DEFAULTS} onRun={handleRun} loading={loading} />
            {result && (
              <div style={{ background: '#fff', borderRadius: 10, padding: 16, border: '1px solid #dde' }}>
                <RiskPanel risk={result.risk_score} srp={result.srp_point} />
              </div>
            )}
          </div>

          {/* Right: Charts + Economics */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {result ? (
              <>
                <div style={{ background: '#fff', borderRadius: 10, padding: 18, border: '1px solid #dde' }}>
                  <CycleChart
                    timeline={result.cycle_result.full_cycle_timeline}
                    phaseBoundaries={result.cycle_result.phase_boundaries}
                  />
                </div>
                <div style={{ background: '#fff', borderRadius: 10, padding: 18, border: '1px solid #dde' }}>
                  <EconomicsDashboard
                    economics={result.economics}
                    injection={result.cycle_result.injection_summary}
                    cycleOil={result.cycle_result.cycle_oil}
                    cycleSteam={result.cycle_result.cycle_steam}
                    sor={result.cycle_result.SOR}
                  />
                </div>
              </>
            ) : (
              <div style={{
                background: '#fff', borderRadius: 10, padding: 50, border: '1px dashed #ccc',
                textAlign: 'center', color: '#aaa',
              }}>
                <div style={{ fontSize: 44, marginBottom: 12 }}>⚙️</div>
                <h4 style={{ margin: '0 0 6px', color: '#555' }}>Digital Twin Ready</h4>
                <p style={{ margin: 0, fontSize: 13 }}>Configure injection and pumping parameters on the left and click <strong>Run Twin Simulation</strong>.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Optimization View */}
      {activeTab === 'optimization' && (
        <OptimizationPanel
          result={optResult}
          loading={optLoading}
          onRunOptimization={handleRunOptimization}
        />
      )}
    </div>
  )
}
