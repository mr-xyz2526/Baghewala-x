import React, { useState, useCallback } from 'react'
import { api } from '../api/client'
import { ControlPanel } from '../components/ControlPanel'
import { EconomicsDashboard } from '../components/EconomicsDashboard'
import { RiskPanel } from '../components/RiskPanel'
import { CycleChart } from '../charts/CycleChart'
import type { TwinRunRequest, TwinRunResult } from '../types'

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
  const [result, setResult] = useState<TwinRunResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

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

  return (
    <div style={{ maxWidth: 1280, margin: '0 auto', padding: '16px 20px', fontFamily: 'system-ui, sans-serif' }}>
      {/* Header */}
      <div style={{
        background: 'linear-gradient(135deg, #1a2980, #26d0ce)',
        borderRadius: 12, padding: '18px 24px', marginBottom: 20, color: '#fff',
      }}>
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800 }}>BAGHEWALA-X Digital Twin</h1>
        <p style={{ margin: '4px 0 0', fontSize: 13, opacity: 0.85 }}>
          PS SIH26120 · Cyclic Steam Stimulation Simulator · Synthetic Data Only
        </p>
      </div>

      {/* Disclaimer banner */}
      <div style={{
        background: '#fff8e1', border: '1px solid #ffe082', borderRadius: 8,
        padding: '8px 14px', marginBottom: 18, fontSize: 12, color: '#7a5c00',
      }}>
        <strong>Prototype Notice:</strong> All results use <em>synthetic parameters</em>.
        No field calibration claimed. Model card: <code>docs/MODEL_CARD.md</code>.
      </div>

      {/* Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 20, alignItems: 'start' }}>
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
          {error && (
            <div style={{ background: '#fdecea', border: '1px solid #f5c6cb', borderRadius: 8, padding: 12, color: '#842029' }}>
              <strong>Error:</strong> {error}
            </div>
          )}

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
              background: '#fff', borderRadius: 10, padding: 40, border: '1px dashed #ccc',
              textAlign: 'center', color: '#aaa',
            }}>
              <div style={{ fontSize: 40, marginBottom: 10 }}>⚙️</div>
              <p>Configure parameters on the left and click <strong>Run Twin Simulation</strong>.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
