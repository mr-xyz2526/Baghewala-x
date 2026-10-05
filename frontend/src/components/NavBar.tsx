import React from 'react'
import type { NavScreen, TwinMode } from '../App'

interface Props {
  screen: NavScreen
  onNavigate: (s: NavScreen) => void
  twinMode: TwinMode
  backendOk: boolean | null
  twinLoading: boolean
}

const TABS: { id: NavScreen; label: string; icon: string }[] = [
  { id: 'field',    label: 'FIELD',    icon: '⬡' },
  { id: 'twin',     label: 'WELL TWIN', icon: '⬡' },
  { id: 'css',      label: 'CSS',      icon: '♨' },
  { id: 'srp',      label: 'SRP',      icon: '⬆' },
  { id: 'optimize', label: 'OPTIMIZE', icon: '◎' },
  { id: 'risk',     label: 'RISK',     icon: '⚠' },
  { id: 'whatif',   label: 'WHAT-IF',  icon: '∿' },
  { id: 'history',  label: 'HISTORY',  icon: '⏱' },
]

export function NavBar({ screen, onNavigate, twinMode, backendOk, twinLoading }: Props) {
  const dotClass = twinLoading ? 'sim' : (twinMode === 'SYNCHRONIZED' ? '' : 'sim')

  return (
    <nav className="navbar">
      {/* Brand */}
      <div className="navbar-brand" style={{ cursor: 'default' }}>
        <div className="navbar-logo" style={{ fontSize: 16 }}>⛽</div>
        <div>
          <div className="navbar-brand-name">BAGHEWALA-X</div>
          <div className="navbar-brand-sub">Digital Twin · SIH26120</div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="nav-tabs">
        {TABS.map(tab => (
          <button
            key={tab.id}
            className={`nav-tab ${screen === tab.id ? 'active' : ''}`}
            onClick={() => onNavigate(tab.id)}
            title={tab.label}
          >
            <span className="nav-tab-icon">{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Right: Status */}
      <div className="status-bar">
        {twinLoading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div className="spinner" />
            <span style={{ fontSize: 10, color: 'var(--amber)', fontWeight: 600, letterSpacing: '0.06em' }}>
              COMPUTING…
            </span>
          </div>
        )}

        <div className="twin-status">
          <div className={`status-dot ${dotClass}`} />
          <div>
            <div className="twin-status-label">DIGITAL TWIN</div>
            <div style={{ fontSize: 10, color: twinMode === 'SYNCHRONIZED' ? 'var(--green)' : 'var(--amber)', fontWeight: 700 }}>
              ● {twinMode === 'SYNCHRONIZED' ? 'SYNCHRONIZED' : 'SIMULATION MODE'}
            </div>
          </div>
        </div>

        <div style={{ fontSize: 10, color: 'var(--text-label)', textAlign: 'right' }}>
          <div>SYNTHETIC DATA</div>
          <div style={{
            color: backendOk === null ? 'var(--text-muted)'
              : backendOk ? 'var(--green)' : 'var(--red)',
          }}>
            {backendOk === null ? '○ CHECKING' : backendOk ? '● API OK' : '● BACKEND OFFLINE'}
          </div>
        </div>
      </div>
    </nav>
  )
}
