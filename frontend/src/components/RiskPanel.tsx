import React from 'react'
import type { RiskScore, SRPPoint } from '../types'

const RISK_COLOR = (v: number) => v > 0.7 ? '#e74c3c' : v > 0.35 ? '#e67e22' : '#27ae60'

interface Props {
  risk: RiskScore
  srp: SRPPoint
}

export const RiskPanel: React.FC<Props> = ({ risk, srp }) => {
  const bars: { label: string; value: number }[] = [
    { label: 'Overall Anomaly', value: risk.anomaly_probability },
    { label: 'Rod Float Risk', value: risk.rod_floating_risk },
    { label: 'Impact/Overload', value: risk.impact_risk },
    { label: 'Equipment Risk', value: risk.equipment_risk },
  ]

  return (
    <div>
      <h3 style={{ marginBottom: 12, color: '#333' }}>Risk & Anomaly Panel</h3>

      {/* Anomaly class badge */}
      <div style={{ marginBottom: 14, display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{
          background: risk.anomaly_class === 'NORMAL' ? '#27ae60' : '#e74c3c',
          color: '#fff', borderRadius: 20, padding: '4px 14px', fontWeight: 700, fontSize: 13,
        }}>{risk.anomaly_class}</span>
        <span style={{ color: '#888', fontSize: 12 }}>
          Probability: {(risk.anomaly_probability * 100).toFixed(0)}%
        </span>
      </div>

      {/* Risk gauges */}
      {bars.map(b => (
        <div key={b.label} style={{ marginBottom: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 3 }}>
            <span>{b.label}</span>
            <span style={{ fontWeight: 700, color: RISK_COLOR(b.value) }}>
              {(b.value * 100).toFixed(0)}%
            </span>
          </div>
          <div style={{ background: '#eee', borderRadius: 4, height: 8 }}>
            <div style={{
              width: `${(b.value * 100).toFixed(0)}%`, background: RISK_COLOR(b.value),
              height: 8, borderRadius: 4, transition: 'width 0.4s',
            }} />
          </div>
        </div>
      ))}

      {/* Flags */}
      {risk.flags.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <strong style={{ fontSize: 12, color: '#e74c3c' }}>Active Flags:</strong>
          <ul style={{ margin: '4px 0', paddingLeft: 18 }}>
            {risk.flags.map((f, i) => <li key={i} style={{ fontSize: 12, color: '#666', marginBottom: 2 }}>{f}</li>)}
          </ul>
        </div>
      )}

      {/* SRP Summary */}
      <div style={{ marginTop: 16, borderTop: '1px solid #eee', paddingTop: 12 }}>
        <strong style={{ fontSize: 12, color: '#555' }}>SRP Metrics (at {srp.spm.toFixed(1)} SPM)</strong>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginTop: 6 }}>
          {[
            ['Peak Rod Load', srp.peak_rod_load_lbf.toFixed(0) + ' lbf'],
            ['Min Rod Load', srp.min_rod_load_lbf.toFixed(0) + ' lbf'],
            ['Motor Power', srp.motor_power_kw.toFixed(1) + ' kW'],
            ['Torque', srp.torque_indicator_ft_lbf.toFixed(0) + ' ft·lbf'],
            ['Plunger Stroke', srp.plunger_stroke_in.toFixed(1) + '"'],
            ['Stress Indicator', (srp.rod_stress_indicator * 100).toFixed(1) + '%'],
          ].map(([k, v]) => (
            <div key={k as string} style={{ fontSize: 12 }}>
              <span style={{ color: '#888' }}>{k}: </span>
              <span style={{ fontWeight: 600 }}>{v}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
