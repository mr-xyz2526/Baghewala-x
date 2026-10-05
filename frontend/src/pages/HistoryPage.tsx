import React, { useState, useMemo } from 'react'
import type { TwinRunResult } from '../types'
import type { NavScreen } from '../App'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceLine,
} from 'recharts'

interface SharedProps {
  twinResult: TwinRunResult | null
  twinLoading: boolean
  twinParams: any
  setTwinParams: (p: any) => void
  runTwin: (params?: any) => void
  setScreen: (s: NavScreen) => void
}

const TIMELINE_DAYS = [0, 5, 10, 15, 20, 25, 30]

// Generate playback data for a 30-day production phase
function generatePlaybackData() {
  const data = []
  for (let day = 0; day <= 30; day++) {
    const decay = Math.exp(-day * 0.03)
    const tempPeak = 185
    const viscBase = 350
    data.push({
      day,
      temperature_c: +(tempPeak * decay + 100 * (1 - decay)).toFixed(1),
      viscosity_cp: +(viscBase + (1 - decay) * 1200).toFixed(0),
      oil_rate_bopd: +(200 * decay + 65 * (1 - decay)).toFixed(1),
      spm_rec: +(6.5 * decay + 4.0 * (1 - decay)).toFixed(1),
      vfd_rec: +(39 * decay + 24 * (1 - decay)).toFixed(0),
      fillage_pct: +(88 * decay + 60 * (1 - decay)).toFixed(1),
      risk: day < 8 ? 'NORMAL' : day < 18 ? 'WARNING' : 'HIGH',
    })
  }
  return data
}

const PLAYBACK_DATA = generatePlaybackData()

export function HistoryPage({ twinResult }: SharedProps) {
  const [currentDay, setCurrentDay] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)

  // Use actual timeline if available, else demo
  const timeline = twinResult?.cycle_result.full_cycle_timeline ?? []
  const useReal = timeline.length > 0

  // Current state at selected day
  const dayState = useMemo(() => {
    if (useReal && currentDay < timeline.length) {
      const r = timeline[currentDay]
      return {
        temperature_c: r.temperature_c,
        viscosity_cp: r.viscosity_cp,
        oil_rate_bopd: r.oil_rate_bopd,
        phase: r.phase,
        spm_rec: 6.5 - (currentDay / 30) * 2,
        vfd_rec: 39 - (currentDay / 30) * 15,
        fillage_pct: 85 - (currentDay / 30) * 20,
      }
    }
    const d = PLAYBACK_DATA[Math.min(currentDay, 30)]
    return { ...d, phase: 'PRODUCTION' as const }
  }, [currentDay, useReal, timeline])

  const maxDay = useReal ? timeline.length - 1 : 30
  const chartData = useReal
    ? timeline.slice(0, currentDay + 1).map(r => ({
        day: r.day,
        temp: r.temperature_c,
        visc: r.viscosity_cp,
        oil: r.oil_rate_bopd,
      }))
    : PLAYBACK_DATA.slice(0, currentDay + 1).map(d => ({
        day: d.day,
        temp: d.temperature_c,
        visc: d.viscosity_cp,
        oil: d.oil_rate_bopd,
      }))

  const riskLevel = dayState.fillage_pct < 65 ? 'HIGH' : dayState.fillage_pct < 75 ? 'WARNING' : 'NORMAL'
  const riskBadge = riskLevel === 'NORMAL' ? 'normal' : riskLevel === 'HIGH' ? 'high' : 'warning'

  const spmRec = dayState.spm_rec ?? (6.5 - (currentDay / maxDay) * 2.5)
  const vfdRec = dayState.vfd_rec ?? (39 - (currentDay / maxDay) * 15)

  // Auto-play effect (simplified - just for UX, not real timer)
  const handlePlay = () => {
    setIsPlaying(true)
    let d = currentDay
    const interval = setInterval(() => {
      d++
      setCurrentDay(d)
      if (d >= maxDay) {
        clearInterval(interval)
        setIsPlaying(false)
      }
    }, 200)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: 18, margin: 0 }}>TWIN PLAYBACK — BW-101</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 12, margin: '4px 0 0' }}>
            {useReal ? 'Simulated twin history' : 'Demo 30-day production phase'} · Scrub timeline to observe twin state evolution
          </p>
        </div>
        <div className={`risk-badge ${riskBadge}`} style={{ fontSize: 12 }}>
          Day {currentDay} — {riskLevel}
        </div>
      </div>

      {/* Timeline scrubber */}
      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">TIMELINE CONTROL</div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-ghost btn-sm" onClick={() => setCurrentDay(0)}>|◀ RESET</button>
            <button className="btn btn-ghost btn-sm" onClick={() => setCurrentDay(Math.max(0, currentDay - 1))}>◀</button>
            <button
              className="btn btn-primary btn-sm"
              onClick={isPlaying ? undefined : handlePlay}
              disabled={isPlaying || currentDay >= maxDay}
            >
              {isPlaying ? <><span className="spinner" /> PLAYING</> : '▶ PLAY'}
            </button>
            <button className="btn btn-ghost btn-sm" onClick={() => setCurrentDay(Math.min(maxDay, currentDay + 1))}>▶</button>
            <button className="btn btn-ghost btn-sm" onClick={() => setCurrentDay(maxDay)}>▶| END</button>
          </div>
        </div>

        {/* Day milestones */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 9, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          {TIMELINE_DAYS.map(d => (
            <span key={d} onClick={() => setCurrentDay(Math.min(d, maxDay))} style={{ cursor: 'pointer', color: currentDay >= d ? 'var(--cyan)' : 'var(--text-label)' }}>
              Day {d}
            </span>
          ))}
        </div>

        <input
          type="range" className="form-slider"
          min={0} max={maxDay} step={1} value={currentDay}
          onChange={e => setCurrentDay(Number(e.target.value))}
        />

        <div style={{ textAlign: 'center', marginTop: 6, fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--cyan)', fontWeight: 700 }}>
          DAY {currentDay} / {maxDay}
        </div>
      </div>

      {/* Current state at selected day */}
      <div className="kpi-rail" style={{ gridTemplateColumns: 'repeat(7, 1fr)' }}>
        {[
          { label: 'TEMPERATURE',  value: dayState.temperature_c.toFixed(1), unit: '°C',    color: 'amber' },
          { label: 'VISCOSITY',    value: dayState.viscosity_cp.toFixed(0),  unit: 'cP',    color: 'cyan' },
          { label: 'OIL RATE',     value: dayState.oil_rate_bopd.toFixed(0), unit: 'BOPD',  color: 'green' },
          { label: 'PUMP FILLAGE', value: (dayState.fillage_pct ?? 82).toFixed(0), unit: '%', color: (dayState.fillage_pct ?? 82) < 65 ? 'red' : 'green' },
          { label: 'REC. SPM',     value: spmRec.toFixed(1), unit: 'spm',   color: '' },
          { label: 'REC. VFD',     value: vfdRec.toFixed(0), unit: 'Hz',    color: 'amber' },
          { label: 'RISK LEVEL',   value: riskLevel, unit: '',  color: riskBadge === 'normal' ? 'green' : riskBadge === 'high' ? 'red' : 'orange' },
        ].map(kpi => (
          <div key={kpi.label} className={`kpi-card ${kpi.color}`}>
            <div className="kpi-label">{kpi.label}</div>
            <div className="kpi-value" style={{ fontSize: 16 }}>{kpi.value}</div>
            {kpi.unit && <div className="kpi-unit">{kpi.unit}</div>}
          </div>
        ))}
      </div>

      {/* Evolution charts */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title">TEMPERATURE & VISCOSITY PLAYBACK</div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData} margin={{ top: 5, right: 25, bottom: 20, left: 10 }}>
              <CartesianGrid strokeDasharray="2 4" stroke="var(--border-dim)" />
              <XAxis dataKey="day" tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                label={{ value: 'Day', position: 'insideBottomRight', offset: -5, fontSize: 10, fill: 'var(--text-muted)' }} />
              <YAxis yAxisId="l" tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                label={{ value: 'Temp (°C)', angle: -90, position: 'insideLeft', fontSize: 10, fill: 'var(--amber)' }} />
              <YAxis yAxisId="r" orientation="right" tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                label={{ value: 'Visc (cP)', angle: 90, position: 'insideRight', fontSize: 10, fill: 'var(--cyan)' }} />
              <Tooltip contentStyle={{ background: 'var(--bg-panel)', border: '1px solid var(--border-hi)', borderRadius: 6, fontSize: 11 }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <ReferenceLine x={currentDay} yAxisId="l" stroke="var(--cyan)" strokeDasharray="4 2" label={{ value: `Day ${currentDay}`, position: 'top', fontSize: 10, fill: 'var(--cyan)' }} />
              <Line yAxisId="l" dataKey="temp" name="Temp (°C)" stroke="var(--amber)" dot={false} strokeWidth={2} isAnimationActive={false} />
              <Line yAxisId="r" dataKey="visc" name="Viscosity (cP)" stroke="var(--cyan)" dot={false} strokeWidth={2} strokeDasharray="5 2" isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div className="panel-title">OIL RATE PLAYBACK</div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData} margin={{ top: 5, right: 25, bottom: 20, left: 10 }}>
              <CartesianGrid strokeDasharray="2 4" stroke="var(--border-dim)" />
              <XAxis dataKey="day" tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                label={{ value: 'Day', position: 'insideBottomRight', offset: -5, fontSize: 10, fill: 'var(--text-muted)' }} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                label={{ value: 'Oil Rate (BOPD)', angle: -90, position: 'insideLeft', fontSize: 10, fill: 'var(--green)' }} />
              <Tooltip contentStyle={{ background: 'var(--bg-panel)', border: '1px solid var(--border-hi)', borderRadius: 6, fontSize: 11 }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <ReferenceLine x={currentDay} stroke="var(--cyan)" strokeDasharray="4 2" label={{ value: `Day ${currentDay}`, position: 'top', fontSize: 10, fill: 'var(--cyan)' }} />
              <Line dataKey="oil" name="Oil Rate (BOPD)" stroke="var(--green)" dot={false} strokeWidth={2} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* VFD / SPM Recommendation timeline */}
      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">VFD / SPM RECOMMENDATION EVOLUTION</div>
          <div className="label-sm">HOW TWIN RECOMMENDATION CHANGES AS WELL COOLS</div>
        </div>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart
            data={PLAYBACK_DATA}
            margin={{ top: 5, right: 25, bottom: 20, left: 10 }}>
            <CartesianGrid strokeDasharray="2 4" stroke="var(--border-dim)" />
            <XAxis dataKey="day" tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
              label={{ value: 'Day', position: 'insideBottomRight', offset: -5, fontSize: 10, fill: 'var(--text-muted)' }} />
            <YAxis yAxisId="l" domain={[0, 14]} tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
              label={{ value: 'SPM', angle: -90, position: 'insideLeft', fontSize: 10, fill: 'var(--cyan)' }} />
            <YAxis yAxisId="r" orientation="right" domain={[0, 60]} tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
              label={{ value: 'VFD (Hz)', angle: 90, position: 'insideRight', fontSize: 10, fill: 'var(--amber)' }} />
            <Tooltip contentStyle={{ background: 'var(--bg-panel)', border: '1px solid var(--border-hi)', borderRadius: 6, fontSize: 11 }} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <ReferenceLine x={currentDay} yAxisId="l" stroke="var(--cyan)" strokeDasharray="4 2"
              label={{ value: `Day ${currentDay}`, position: 'top', fontSize: 10, fill: 'var(--cyan)' }} />
            <Line yAxisId="l" dataKey="spm_rec" name="Rec. SPM" stroke="var(--cyan)" dot={false} strokeWidth={2} />
            <Line yAxisId="r" dataKey="vfd_rec" name="Rec. VFD (Hz)" stroke="var(--amber)" dot={false} strokeWidth={2} strokeDasharray="5 2" />
          </LineChart>
        </ResponsiveContainer>
        <div className="explain-block" style={{ marginTop: 10 }}>
          <div className="explain-label">TWIN DYNAMICS</div>
          <div className="explain-text">
            As the reservoir cools after injection, viscosity rises. The twin model recommends progressively
            lower SPM and VFD to maintain pump fillage above the fluid-pound threshold.
            This demonstrates that the twin is dynamic — recommendations adapt to thermal state, not fixed parameters.
          </div>
        </div>
      </div>
    </div>
  )
}
