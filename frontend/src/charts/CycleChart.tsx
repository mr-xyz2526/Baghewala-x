import React from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ReferenceArea, ResponsiveContainer,
} from 'recharts'
import type { CycleTimelineRecord } from '../types'

interface Props {
  timeline: CycleTimelineRecord[]
  phaseBoundaries: {
    injection: { start_day: number; end_day: number }
    soak: { start_day: number; end_day: number }
    production: { start_day: number; end_day: number }
  }
}

const PHASE_COLORS: Record<string, string> = {
  INJECTION: '#ffdddd',
  SOAKING: '#fff7d1',
  PRODUCTION: '#d9ead3',
}

export const CycleChart: React.FC<Props> = ({ timeline, phaseBoundaries }) => {
  const data = timeline.map(r => ({
    day: r.day,
    temp: +r.temperature_c.toFixed(1),
    visc: +r.viscosity_cp.toFixed(0),
    oil: +r.oil_rate_bopd.toFixed(1),
    steam: +r.steam_rate_tpd.toFixed(0),
  }))

  const pb = phaseBoundaries

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Temperature + Viscosity */}
      <div>
        <h4 style={{ margin: '0 0 4px', color: '#555' }}>Reservoir Temperature & Oil Viscosity</h4>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="day" label={{ value: 'Day', position: 'insideBottomRight', offset: -5 }} />
            <YAxis yAxisId="left" stroke="#c0392b" label={{ value: 'Temp (°C)', angle: -90, position: 'insideLeft' }} />
            <YAxis yAxisId="right" orientation="right" stroke="#2980b9" scale="log" domain={['auto', 'auto']}
              label={{ value: 'Visc (cP)', angle: 90, position: 'insideRight' }} />
            <Tooltip />
            <Legend />
            <ReferenceArea yAxisId="left" x1={pb.injection.start_day} x2={pb.injection.end_day} fill={PHASE_COLORS.INJECTION} />
            <ReferenceArea yAxisId="left" x1={pb.soak.start_day} x2={pb.soak.end_day} fill={PHASE_COLORS.SOAKING} />
            <ReferenceArea yAxisId="left" x1={pb.production.start_day} x2={pb.production.end_day} fill={PHASE_COLORS.PRODUCTION} />
            <Line yAxisId="left" dataKey="temp" stroke="#c0392b" name="Temp (°C)" dot={false} strokeWidth={2} />
            <Line yAxisId="right" dataKey="visc" stroke="#2980b9" name="Viscosity (cP)" dot={false} strokeWidth={2} strokeDasharray="4 2" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Oil Rate + Steam */}
      <div>
        <h4 style={{ margin: '0 0 4px', color: '#555' }}>Oil Rate & Steam Injection</h4>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="day" label={{ value: 'Day', position: 'insideBottomRight', offset: -5 }} />
            <YAxis yAxisId="left" stroke="#27ae60" label={{ value: 'Oil (BOPD)', angle: -90, position: 'insideLeft' }} />
            <YAxis yAxisId="right" orientation="right" stroke="#8e44ad"
              label={{ value: 'Steam (t/d)', angle: 90, position: 'insideRight' }} />
            <Tooltip />
            <Legend />
            <ReferenceArea yAxisId="left" x1={pb.injection.start_day} x2={pb.injection.end_day} fill={PHASE_COLORS.INJECTION} />
            <ReferenceArea yAxisId="left" x1={pb.soak.start_day} x2={pb.soak.end_day} fill={PHASE_COLORS.SOAKING} />
            <ReferenceArea yAxisId="left" x1={pb.production.start_day} x2={pb.production.end_day} fill={PHASE_COLORS.PRODUCTION} />
            <Line yAxisId="left" dataKey="oil" stroke="#27ae60" name="Oil (BOPD)" dot={false} strokeWidth={2} />
            <Line yAxisId="right" dataKey="steam" stroke="#8e44ad" name="Steam (t/d)" dot={false} strokeWidth={2} strokeDasharray="4 2" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
