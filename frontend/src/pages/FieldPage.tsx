import React, { useState } from 'react'
import type { TwinRunResult } from '../types'
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

const DEMO_WELLS = [
  { id: 'BW-101', health: 'healthy',    rate: 187, phase: 'PRODUCTION', temp: 184, visc: 420, spm: 6.0,  vfd: 36, fillage: 82, sor: 4.1, risk: 'NORMAL' },
  { id: 'BW-102', health: 'healthy',    rate: 203, phase: 'PRODUCTION', temp: 196, visc: 310, spm: 6.5,  vfd: 39, fillage: 88, sor: 3.8, risk: 'NORMAL' },
  { id: 'BW-103', health: 'monitoring', rate: 142, phase: 'SOAKING',    temp: 245, visc: 180, spm: 0,    vfd: 0,  fillage: 0,  sor: 5.2, risk: 'WARNING' },
  { id: 'BW-104', health: 'risk',       rate: 89,  phase: 'PRODUCTION', temp: 148, visc: 1200,spm: 7.5,  vfd: 45, fillage: 48, sor: 8.9, risk: 'HIGH' },
  { id: 'BW-105', health: 'healthy',    rate: 221, phase: 'PRODUCTION', temp: 201, visc: 280, spm: 5.5,  vfd: 33, fillage: 91, sor: 3.6, risk: 'NORMAL' },
  { id: 'BW-106', health: 'healthy',    rate: 198, phase: 'INJECTION',  temp: 260, visc: 120, spm: 0,    vfd: 0,  fillage: 0,  sor: 4.4, risk: 'NORMAL' },
  { id: 'BW-107', health: 'healthy',    rate: 176, phase: 'PRODUCTION', temp: 179, visc: 460, spm: 6.0,  vfd: 36, fillage: 79, sor: 4.7, risk: 'NORMAL' },
  { id: 'BW-108', health: 'monitoring', rate: 131, phase: 'PRODUCTION', temp: 161, visc: 820, spm: 8.0,  vfd: 48, fillage: 61, sor: 6.1, risk: 'WARNING' },
  { id: 'BW-109', health: 'healthy',    rate: 245, phase: 'PRODUCTION', temp: 208, visc: 245, spm: 5.0,  vfd: 30, fillage: 93, sor: 3.2, risk: 'NORMAL' },
  { id: 'BW-110', health: 'healthy',    rate: 211, phase: 'SOAKING',    temp: 251, visc: 160, spm: 0,    vfd: 0,  fillage: 0,  sor: 4.0, risk: 'NORMAL' },
  { id: 'BW-111', health: 'monitoring', rate: 119, phase: 'PRODUCTION', temp: 155, visc: 960, spm: 7.0,  vfd: 42, fillage: 55, sor: 7.2, risk: 'WARNING' },
  { id: 'BW-112', health: 'healthy',    rate: 167, phase: 'PRODUCTION', temp: 176, visc: 510, spm: 6.0,  vfd: 36, fillage: 77, sor: 4.9, risk: 'NORMAL' },
]

const DEMO_ALERTS = [
  { id: 1, well: 'BW-104', msg: 'Pump fillage dropped to 48% — fluid pound risk elevated', severity: 'high', time: '12:41' },
  { id: 2, well: 'BW-108', msg: 'Viscosity rising (820 cP) — reduce SPM recommended', severity: 'warning', time: '11:52' },
  { id: 3, well: 'BW-111', msg: 'Fillage 55% — monitor for fluid pound conditions', severity: 'warning', time: '10:18' },
]

function generateTrendData() {
  const data = []
  for (let day = 0; day <= 30; day++) {
    const decay = Math.exp(-day * 0.025)
    data.push({
      day,
      temp: +(190 * decay + 100 * (1 - decay) + (Math.random() - 0.5) * 5).toFixed(1),
      visc: +(350 + (1 - decay) * 800 + (Math.random() - 0.5) * 40).toFixed(0),
      oil:  +(220 * decay + 80 * (1 - decay) + (Math.random() - 0.5) * 8).toFixed(1),
    })
  }
  return data
}

const TREND_DATA = generateTrendData()

export function FieldPage({ twinResult, twinLoading, runTwin, setScreen }: SharedProps) {
  const [selectedWell, setSelectedWell] = useState('BW-101')
  const well = DEMO_WELLS.find(w => w.id === selectedWell) ?? DEMO_WELLS[0]

  const fieldOilRate = DEMO_WELLS.reduce((a, w) => a + (w.phase !== 'INJECTION' && w.phase !== 'SOAKING' ? w.rate : 0), 0)
  const healthyCount = DEMO_WELLS.filter(w => w.health === 'healthy').length
  const monitorCount = DEMO_WELLS.filter(w => w.health === 'monitoring').length
  const riskCount    = DEMO_WELLS.filter(w => w.health === 'risk').length

  // Use twinResult for selected well if it's BW-101
  const liveTemp = selectedWell === 'BW-101' && twinResult
    ? twinResult.cycle_result.full_cycle_timeline.slice(-1)[0]?.temperature_c ?? well.temp
    : well.temp
  const liveVisc = selectedWell === 'BW-101' && twinResult
    ? twinResult.cycle_result.full_cycle_timeline.slice(-1)[0]?.viscosity_cp ?? well.visc
    : well.visc
  const liveOil = selectedWell === 'BW-101' && twinResult
    ? twinResult.srp_point.oil_rate_bopd
    : well.rate
  const liveSpm = selectedWell === 'BW-101' && twinResult
    ? twinResult.srp_point.spm
    : well.spm
  const liveFillage = selectedWell === 'BW-101' && twinResult
    ? twinResult.srp_point.pump_fillage_pct
    : well.fillage

  const fillageColor = liveFillage < 60 ? 'var(--red)' : liveFillage < 75 ? 'var(--orange)' : 'var(--green)'

  const healthStatusLabel = (h: string) =>
    h === 'healthy' ? 'HEALTHY' : h === 'monitoring' ? 'MONITOR' : 'HIGH RISK'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {/* Page header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h2 style={{ fontSize: 18, margin: 0 }}>FIELD COMMAND CENTER</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 12, margin: '4px 0 0' }}>
            Baghewala Field · {DEMO_WELLS.length} Wells · Synthetic Demo Data
          </p>
        </div>
        <div style={{ fontSize: 10, color: 'var(--text-muted)', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
          <div>LAST SYNC</div>
          <div style={{ color: 'var(--cyan)' }}>SIMULATION MODE</div>
        </div>
      </div>

      {/* KPI Rail */}
      <div className="kpi-rail" style={{ gridTemplateColumns: 'repeat(8, 1fr)' }}>
        {[
          { label: 'Active Wells', value: DEMO_WELLS.length, unit: '', color: 'cyan' },
          { label: 'Healthy',       value: healthyCount, unit: '', color: 'green' },
          { label: 'Monitoring',    value: monitorCount, unit: '', color: 'amber' },
          { label: 'High Risk',     value: riskCount,    unit: '', color: 'red' },
          { label: 'Field Oil Rate',value: fieldOilRate, unit: 'BOPD', color: 'green' },
          { label: 'Steam Usage',   value: '800', unit: 't/d', color: 'amber' },
          { label: 'Energy / bbl',  value: '4.8', unit: 'GJ/bbl', color: 'orange' },
          { label: 'Active Alerts', value: DEMO_ALERTS.length, unit: '', color: 'red' },
        ].map(kpi => (
          <div key={kpi.label} className={`kpi-card ${kpi.color}`}>
            <div className="kpi-label">{kpi.label}</div>
            <div className="kpi-value">{kpi.value}</div>
            {kpi.unit && <div className="kpi-unit">{kpi.unit}</div>}
          </div>
        ))}
      </div>

      {/* Main 3-column grid */}
      <div className="grid-3col">

        {/* LEFT: Well Grid */}
        <div className="panel" style={{ padding: 12 }}>
          <div className="panel-header">
            <div className="panel-title">WELL PAD MAP</div>
            <div className="label-sm">CLICK TO SELECT</div>
          </div>
          <div className="well-grid">
            {DEMO_WELLS.map(w => (
              <div
                key={w.id}
                className={`well-cell ${w.health} ${selectedWell === w.id ? 'selected' : ''}`}
                onClick={() => setSelectedWell(w.id)}
              >
                <div style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: w.health === 'healthy' ? 'var(--green)' : w.health === 'monitoring' ? 'var(--amber)' : 'var(--red)',
                  marginBottom: 4,
                  boxShadow: `0 0 5px ${w.health === 'healthy' ? 'var(--green)' : w.health === 'monitoring' ? 'var(--amber)' : 'var(--red)'}`,
                }} />
                <div className="well-cell-id">{w.id}</div>
                <div className="well-cell-status" style={{
                  color: w.health === 'healthy' ? 'var(--green)' : w.health === 'monitoring' ? 'var(--amber)' : 'var(--red)',
                }}>
                  {healthStatusLabel(w.health)}
                </div>
                <div style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 3, fontFamily: 'var(--font-mono)' }}>
                  {w.phase === 'INJECTION' ? '♨ INJ' : w.phase === 'SOAKING' ? '◎ SOAK' : `${w.rate} BOPD`}
                </div>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--border-dim)' }}>
            <div className="label-xs" style={{ marginBottom: 6 }}>LEGEND</div>
            <div style={{ display: 'flex', gap: 12, fontSize: 10 }}>
              <span style={{ color: 'var(--green)' }}>● Healthy ({healthyCount})</span>
              <span style={{ color: 'var(--amber)' }}>● Monitor ({monitorCount})</span>
              <span style={{ color: 'var(--red)' }}>● Risk ({riskCount})</span>
            </div>
          </div>
        </div>

        {/* CENTER: Selected well telemetry */}
        <div className="panel">
          <div className="panel-header">
            <div>
              <div className="panel-title">WELL {well.id} — LIVE TELEMETRY</div>
              <div className="panel-subtitle">
                {well.phase === 'INJECTION' ? 'Steam Injection Phase' :
                 well.phase === 'SOAKING'   ? 'Thermal Soak Phase' : 'Production Phase'}
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <div className={`phase-badge ${well.phase.toLowerCase()}`}>
                {well.phase === 'INJECTION' ? '♨' : well.phase === 'SOAKING' ? '◎' : '⬆'} {well.phase}
              </div>
              <div className={`risk-badge ${well.risk === 'NORMAL' ? 'normal' : well.risk === 'HIGH' ? 'high' : 'warning'}`}>
                {well.risk}
              </div>
            </div>
          </div>

          {/* Telemetry grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 14 }}>
            {[
              { label: 'RESERVOIR TEMP', value: `${liveTemp.toFixed(1)}`, unit: '°C', color: 'amber' },
              { label: 'OIL VISCOSITY',  value: `${liveVisc.toFixed(0)}`, unit: 'cP', color: 'cyan' },
              { label: 'OIL RATE',       value: `${liveOil.toFixed(0)}`,  unit: 'BOPD', color: 'green' },
              { label: 'SOR',            value: `${well.sor.toFixed(2)}`, unit: 't/bbl', color: well.sor > 7 ? 'red' : well.sor > 5 ? 'orange' : '' },
              { label: 'SPM',            value: `${liveSpm.toFixed(1)}`,  unit: 'str/min', color: '' },
              { label: 'VFD',            value: `${well.vfd}`,            unit: 'Hz', color: 'amber' },
            ].map(item => (
              <div key={item.label} className="panel-card">
                <div className="telem-label">{item.label}</div>
                <div className={`telem-value ${item.color}`} style={{ fontSize: 18 }}>{item.value}</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{item.unit}</div>
              </div>
            ))}
          </div>

          {/* Pump fillage bar */}
          <div style={{ marginBottom: 14 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
              <span className="label-sm">PUMP FILLAGE</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 700, color: fillageColor }}>
                {liveFillage.toFixed(0)}%
              </span>
            </div>
            <div className="risk-bar-track" style={{ height: 8, background: 'var(--border)' }}>
              <div className="risk-bar-fill" style={{ width: `${liveFillage}%`, background: fillageColor }} />
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3 }}>
              {liveFillage < 60 ? '⚠ FLUID POUND RISK' : liveFillage < 75 ? 'MONITOR' : '✓ NORMAL'}
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <button
              className="btn btn-primary"
              style={{ flex: 1 }}
              onClick={() => { runTwin(); setScreen('twin') }}
              disabled={twinLoading}
            >
              {twinLoading ? <><span className="spinner" /> RUNNING…</> : '⬡ OPEN WELL TWIN'}
            </button>
            <button className="btn btn-ghost" onClick={() => setScreen('srp')}>SRP →</button>
            <button className="btn btn-ghost" onClick={() => setScreen('risk')}>RISK →</button>
          </div>
        </div>

        {/* RIGHT: Alerts + Recommendations */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* Alerts */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">ACTIVE ALERTS</div>
              <div className={`risk-badge ${DEMO_ALERTS.length > 0 ? 'warning' : 'normal'}`}>
                {DEMO_ALERTS.length}
              </div>
            </div>
            {DEMO_ALERTS.map(alert => (
              <div key={alert.id} style={{
                borderLeft: `3px solid ${alert.severity === 'high' ? 'var(--red)' : 'var(--amber)'}`,
                paddingLeft: 10, marginBottom: 10,
              }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: alert.severity === 'high' ? 'var(--red)' : 'var(--amber)', marginBottom: 2 }}>
                  {alert.well} · {alert.time}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-primary)', lineHeight: 1.4 }}>{alert.msg}</div>
              </div>
            ))}
          </div>

          {/* Top recommendation */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">TOP ACTION</div>
            </div>
            <div className="explain-block">
              <div className="explain-label">RECOMMENDATION</div>
              <div className="explain-text">
                BW-104 pump fillage at 48%. Reduce SPM from 7.5 → 5.5 to allow well to refill.
                Current viscosity (1200 cP) requires lower pump speed for adequate barrel fill.
              </div>
            </div>
            <div style={{ marginTop: 10, display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)' }}>
              <span>Model confidence</span>
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--green)' }}>DEMO</span>
            </div>
          </div>

          {/* Model status */}
          <div className="panel-card" style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div className="label-sm">TWIN MODEL STATUS</div>
            {[
              { label: 'CSS Engine', status: 'OK', color: 'var(--green)' },
              { label: 'SRP Simulator', status: 'OK', color: 'var(--green)' },
              { label: 'Risk Engine', status: 'OK', color: 'var(--green)' },
              { label: 'Optimizer', status: 'READY', color: 'var(--cyan)' },
            ].map(m => (
              <div key={m.label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <span style={{ color: 'var(--text-muted)' }}>{m.label}</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: m.color, fontWeight: 700 }}>● {m.status}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom: 30-day trend strip */}
      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">30-DAY FIELD TREND — BW-101</div>
          <div className="label-sm">TEMPERATURE · VISCOSITY · OIL RATE</div>
        </div>
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={TREND_DATA} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
            <CartesianGrid strokeDasharray="2 4" stroke="var(--border-dim)" />
            <XAxis dataKey="day" tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
              label={{ value: 'Day', position: 'insideBottomRight', offset: -5, fontSize: 10, fill: 'var(--text-muted)' }} />
            <YAxis yAxisId="l" tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
              label={{ value: '°C / BOPD', angle: -90, position: 'insideLeft', fontSize: 10, fill: 'var(--text-muted)' }} />
            <YAxis yAxisId="r" orientation="right"
              tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
              label={{ value: 'cP', angle: 90, position: 'insideRight', fontSize: 10, fill: 'var(--text-muted)' }} />
            <Tooltip contentStyle={{ background: 'var(--bg-panel)', border: '1px solid var(--border-hi)', borderRadius: 6, fontSize: 11 }} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line yAxisId="l" dataKey="temp" name="Temp (°C)" stroke="var(--amber)" dot={false} strokeWidth={1.5} />
            <Line yAxisId="r" dataKey="visc" name="Viscosity (cP)" stroke="var(--cyan)" dot={false} strokeWidth={1.5} strokeDasharray="4 2" />
            <Line yAxisId="l" dataKey="oil" name="Oil Rate (BOPD)" stroke="var(--green)" dot={false} strokeWidth={1.5} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
